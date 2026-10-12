import asyncio
import logging
import re

import httpx
from ddgs import DDGS

from .config import LLAMA_URL, SYSTEM_PROMPT, TRUNCATE_SENTENCES

log = logging.getLogger("tg-bot.llama")

async def web_search(query: str, max_results: int = 3) -> str:
    def _search():
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            return "\n\n".join(
                f"Title: {r['title']}\nURL: {r['href']}\n{r['body']}"
                for r in results
            )
    try:
        return await asyncio.to_thread(_search)
    except Exception as e:
        log.warning("Web search failed: %s", e)
        return ""

def _needs_search(text: str) -> bool:
    pattern = r'^(o|a|os|as|que|qual|como|por|quando|where|what|why|how|who|when|can|does|is|are|tell|explain)\b'
    return bool(re.match(pattern, text, re.I)) or '?' in text

async def call_llama(messages: list[dict]) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{LLAMA_URL}/v1/chat/completions",
                json={"messages": messages},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return None
    except Exception as e:
        log.warning("LLM call failed: %s", e)
        return None

async def get_reply(text: str, history: list[dict], user_id: int, system_prompt_extra: str = "") -> str | None:
    """Full pipeline: optional web search → build messages → call LLM → truncate."""
    search_context = ""
    if _needs_search(text):
        search_context = await web_search(text)

    base_prompt = SYSTEM_PROMPT or "You are a helpful personal assistant. Be concise. Answer in the user's language."
    if system_prompt_extra:
        base_prompt += f"\n\n{system_prompt_extra}"

    messages = [{"role": "system", "content": base_prompt}]

    if search_context:
        messages.append({"role": "user", "content": f"Web search results for reference:\n\n{search_context}"})
        messages.append({"role": "assistant", "content": "Got it, I'll use these as context."})

    messages.extend(history)
    messages.append({"role": "user", "content": text})

    reply = await call_llama(messages)
    if reply is None:
        return None

    if TRUNCATE_SENTENCES > 0:
        parts = re.split(r'(?<=[.!?])\s+', reply)
        reply = " ".join(parts[:TRUNCATE_SENTENCES])

    return reply   
