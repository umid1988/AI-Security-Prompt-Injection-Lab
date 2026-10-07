"""
Practice chatbot: a local web UI where students try the lab themselves.

The student picks a pipeline (vulnerable / secure) and a page -- one of the
lab pages or HTML they write themselves -- then chats with the "summarizer
bot". Every reply comes with an inspector showing what the model actually
received, so the gap between "what a human sees" and "what the model reads"
is visible on every turn.

Safety: binds to 127.0.0.1 only and never fetches external URLs; pages come
from this folder or from the text box.

Run:
    python chatbot.py                 # sim mode, offline
    LLM_MODE=api python chatbot.py    # real model (needs ANTHROPIC_API_KEY)
Then open http://127.0.0.1:8080
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import agent_app
import secure_app
import vulnerable_app
from llm import complete

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("CHATBOT_PORT", "8080"))
MAX_BODY = 200_000

def _catalog() -> list:
    """Build the page catalog: benign control + the technique library in pages/."""
    items = [{
        "key": "benign", "group": "control", "label": "😊 Toza sahifa (buyruqsiz)",
        "why": "Injection yo'q — nazorat sinovi", "html": _read("benign_page.html"),
    }]
    manifest_path = os.path.join(HERE, "pages", "manifest.json")
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except FileNotFoundError:
        manifest = {}
    for fn in sorted(manifest):
        meta = manifest[fn]
        items.append({
            "key": "pages/" + fn,
            "group": meta.get("group", "concealment" if fn[:2] < "08" else "framing"),
            "label": meta["label"], "why": meta["why"],
            "cmd": meta.get("cmd", ""),
            "goal": meta.get("goal", ""),
            "layer": meta.get("layer", ""),
            "html": _read(os.path.join("pages", fn)),
        })
    return items

PIPELINES = {
    "vulnerable": vulnerable_app,
    "secure": secure_app,
}


def _read(name: str) -> str:
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def chat(pipeline: str, html: str, question: str) -> dict:
    # agent scenarios (tool-using) take a different, action-oriented path
    if agent_app.is_agent_page(html):
        return agent_app.run(pipeline, html)
    app = PIPELINES[pipeline]
    system, user = app.build_request(html)
    if question:
        # the student's own message rides along as the trusted request
        user = f"{user}\n\nUser question: {question}"
    raw = complete(system, user)
    reply = app.check_output(raw) if hasattr(app, "check_output") else raw
    return {
        "reply": reply,
        "blocked": reply != raw,
        "system": system,
        "user": user,
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, _read("chatbot.html").encode(), "text/html; charset=utf-8")
        elif self.path == "/api/pages":
            self._json(200, {"catalog": _catalog()})
        elif self.path == "/api/info":
            self._json(200, {"mode": os.environ.get("LLM_MODE", "sim").lower()})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/chat":
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._json(413, {"error": "page too large"})
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
            pipeline = req.get("pipeline", "vulnerable")
            if pipeline not in PIPELINES:
                return self._json(400, {"error": "unknown pipeline"})
            html = str(req.get("html", ""))
            if not html.strip():
                return self._json(400, {"error": "empty page"})
            self._json(200, chat(pipeline, html, str(req.get("question", "")).strip()))
        except Exception as e:  # show the error in the UI instead of hanging
            self._json(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        sys.stderr.write("[chatbot] " + fmt % args + "\n")


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Chatbot: http://127.0.0.1:{PORT}  (LLM_MODE={os.environ.get('LLM_MODE', 'sim')})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
