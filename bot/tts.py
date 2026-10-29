import asyncio
import logging
import tempfile
import os
from pathlib import Path

log = logging.getLogger("tg-bot.tts")

VOICES_DIR = Path("/media/debian/Models/voices")

VOICE_MAP = {
    "es": "es_AR-daniela-high.onnx",
    "pt": "pt_BR-faber-medium.onnx",
    "en": "en_US-lessac-high.onnx",
}
DEFAULT_VOICE = "es_AR-daniela-high.onnx"


def detect_language(text: str) -> str:
    """Minimal es/pt/en detector for a 3-language personal assistant."""
    t = text.lower()[:300]
    pt_markers = ("ã", "õ", "você", "obrigado", "obrigada", "não", "tá ", "pra ", "pro ", "também", "então", "coisa", "gostei", "beleza")
    es_markers = ("¿", "¡", "gracias", "hola", "tú ", "para ", "también", "dónde", "cómo ", "qué ", "por qué")

    pt_score = sum(1 for m in pt_markers if m in t)
    es_score = sum(1 for m in es_markers if m in t)

    if pt_score > es_score:
        return "pt"
    elif es_score > pt_score:
        return "es"
    else:
        en_markers = ("the", "what", "how", "please", "thank", "hello", "can you", "i want", "i need")
        en_score = sum(1 for m in en_markers if m in t)
        if en_score >= 2:
            return "en"
        return "es"


def get_voice_for_language(lang_code: str) -> Path:
    """Map a language code (e.g. 'pt', 'en', 'es') to a voice file path."""
    if not lang_code:
        return VOICES_DIR / DEFAULT_VOICE
    prefix = lang_code.split("-")[0].lower()
    voice_file = VOICE_MAP.get(prefix, DEFAULT_VOICE)
    path = VOICES_DIR / voice_file
    if path.exists():
        return path
    return VOICES_DIR / DEFAULT_VOICE


async def text_to_ogg(text: str, language_code: str = "es") -> bytes | None:
    """Convert text to OGG/Opus bytes using Piper TTS + ffmpeg."""
    voice = get_voice_for_language(language_code)
    if not voice.exists():
        log.warning("Voice not found: %s", voice)
        return None

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_path = wav_file.name
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
            ogg_path = ogg_file.name

        proc = await asyncio.create_subprocess_exec(
            "piper", "-m", str(voice), "-f", wav_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate(input=text.encode("utf-8"))
        if proc.returncode != 0:
            log.warning("Piper failed: %s", stderr.decode()[:200])
            return None

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", wav_path,
            "-c:a", "libopus", "-b:a", "32k", "-vbr", "on",
            "-application", "voip",
            ogg_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        if proc.returncode != 0:
            log.warning("ffmpeg OGG conversion failed")
            return None

        with open(ogg_path, "rb") as f:
            return f.read()

    except Exception as e:
        log.warning("TTS failed: %s", e)
        return None
    finally:
        for p in (wav_path, ogg_path):
            try:
                os.unlink(p)
            except (OSError, NameError):
                pass   
