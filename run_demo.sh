#!/usr/bin/env bash
# One-shot demo: start server, run vulnerable vs secure, stop server.
set -u
cd "$(dirname "$0")"

pkill -9 -f serve.py 2>/dev/null || true
sleep 1
python serve.py >/tmp/serve.log 2>&1 &
SRV=$!
sleep 2

echo "server: $(curl -s -m3 -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/malicious_page.html)"
echo
echo "===== VULNERABLE / malicious ====="
LLM_MODE=sim python vulnerable_app.py
echo
echo "===== SECURE / malicious ====="
LLM_MODE=sim python secure_app.py
echo
echo "===== SECURE / benign (control) ====="
LLM_MODE=sim python secure_app.py http://localhost:8000/benign_page.html

kill "$SRV" 2>/dev/null || true
wait "$SRV" 2>/dev/null || true
