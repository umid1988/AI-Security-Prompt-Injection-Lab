"""
VULNERABLE "AI summarizer".

The bug: it builds ONE flat prompt where the trusted task and the untrusted
page text live in the same instruction channel, with nothing telling the model
which is which. Anything imperative inside the page is indistinguishable from
the developer's own instructions.

Run:
    python serve.py &                 # host the demo pages on :8000
    LLM_MODE=sim python vulnerable_app.py        # offline, illustrative
    LLM_MODE=api python vulnerable_app.py        # real model (needs API key)
"""

import sys
from fetcher import fetch, extract_text_naive
from llm import complete

SYSTEM = "You are a helpful assistant. Summarize web pages in 2 sentences."


def summarize(url: str) -> str:
    html = fetch(url)
    page_text = extract_text_naive(html)          # <-- pulls hidden text too

    # THE VULNERABILITY: untrusted page_text pasted straight into the prompt.
    prompt = (
        "Please summarize the following web page for me:\n\n"
        + page_text
    )
    return complete(SYSTEM, prompt)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/malicious_page.html"
    print(f"[vulnerable] fetching {url}\n")
    print(summarize(url))
