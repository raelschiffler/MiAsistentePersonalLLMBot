# MiAsistentePersonalLLMBot

Personal Telegram bot powered by a local LLM (llama.cpp) with multimodal
input, web search, image generation (stable-diffusion.cpp), TTS, and
persistent memory.

## Requirements

- Debian 12
- Python 3.11+
- llama.cpp (with Vulkan)
- stable-diffusion.cpp (with Vulkan)
- `poppler-utils`, `ffmpeg`, `gawk`
- Piper TTS voices (optional)

## Setup

```bash
# 1. Clone
git clone <repo-url> && cd MiAsistentePersonalLLMBot

# 2. Venv
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Config
cp config/config.example.json config/config.json
# Edit config.json with your bot token and main_user_id

# 4. Contacts (whitelist)
echo '{}' > config/contacts.json

# 5. Data dirs
mkdir -p data/conversations

# 6. Systemd
sudo cp systemd/llm-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now llm-bot

# 7. Log dir
sudo mkdir -p /var/log/llm-bot
sudo chown $USER:$USER /var/log/llm-bot   

# 8. Commands
| Command | Access | Description |
|---------|--------|-------------|
| `/start` | Whitelisted | Initialize chat |
| `/generate <prompt>` | All | Text-to-image |
| `/remind <time> <msg>` | Owner | Set reminder |
| `/remember <fact>` | Owner | Store memory |
| `/status` | Owner | System health |
| `/listgroups` | Owner | Tracked groups |
| `/setgroupseasoning <id> <text>` | Owner | Group personality |

# 9. Architecture
bot/
  main.py        # Entry, handlers, LLM auto-start
  config.py      # Config loader, whitelist
  handlers.py    # All Telegram handlers
  llama.py       # LLM client, tools, multimodal
  security.py    # Security logging
  contacts.py    # Interaction tracking
  convlog.py     # Per-user conversation logs
  groups.py      # Group tracking
  memory.py      # Persistent facts
  reminders.py   # Persistent reminders
  tts.py         # Piper TTS
  logrotate.py   # Log rotation + cleanup   

# 9. Logs
All output (bot, llama-server, sd-cli) goes to /var/log/llm-bot/llama_server.log.
Rotated per session; old logs auto-deleted when directory exceeds 50 MB.

Then:

```bash
cd ~/Developer/bots/MiAsistentePersonalLLMBot
git init
git add .
git commit -m "v0.1"
git tag v0.1
git remote add origin <your-github-url>
git push -u origin main --tags   
