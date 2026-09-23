"""
Fetch a page and turn it into text for the model.

extract_text_naive()  -- what a careless scraper does: grabs comments, hidden
                         elements, invisible text -- everything. This is the
                         bug that makes injection possible.
extract_text_visible() -- a stricter extractor closer to what a human sees:
                         drops comments, <script>/<style>, and display:none /
                         visibility:hidden / white-on-white nodes.
"""

import re
import urllib.request
from bs4 import BeautifulSoup, Comment


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode("utf-8", "replace")


def extract_text_naive(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # keeps comments, hidden divs, invisible text -- everything as raw text
    text = soup.get_text(separator=" ")
    comments = soup.find_all(string=lambda t: isinstance(t, Comment))
    text += " " + " ".join(c for c in comments)
    return re.sub(r"\s+", " ", text).strip()


def _is_hidden(tag) -> bool:
    style = (tag.get("style") or "").lower().replace(" ", "")
    if "display:none" in style or "visibility:hidden" in style:
        return True
    # crude white-on-white check
    if "color:#ffffff" in style and "background:#ffffff" in style:
        return True
    cls = " ".join(tag.get("class", []))
    return "invisible" in cls


def extract_text_visible(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()
    for t in soup(["script", "style"]):
        t.decompose()
    for t in soup.find_all(True):
        if _is_hidden(t):
            t.decompose()
    # NOTE: this is heuristic. The .invisible class here is styled in <style>,
    # so we also strip by class name above. Real pages need a real renderer.
    return re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
