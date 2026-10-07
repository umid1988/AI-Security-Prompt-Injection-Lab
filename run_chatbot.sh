#!/usr/bin/env bash
# Talaba mashqni o'zi sinaydigan chatbot.
#   bash run_chatbot.sh              # offline sim
#   LLM_MODE=api bash run_chatbot.sh # haqiqiy model (ANTHROPIC_API_KEY kerak)
set -u
cd "$(dirname "$0")"
echo "Ochish: http://127.0.0.1:${CHATBOT_PORT:-8080}"
exec python3 chatbot.py
