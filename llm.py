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


def _simulate(system: str, user: str) -> str:
    """
    Illustrative only. Rule: if an imperative injection marker appears anywhere
    in the prompt text the model receives, the 'model' follows the last such
    instruction -- exactly the recency/authority confusion real models exhibit
    when data and instructions share one channel.
    """
    blob = f"{system}\n{user}"
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
    resp = client.messages.create(
        model=os.environ.get("LLM_MODEL", "claude-3-5-haiku-latest"),
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def complete(system: str, user: str) -> str:
    mode = os.environ.get("LLM_MODE", "sim").lower()
    if mode == "api":
        return _call_api(system, user)
    return _simulate(system, user)
