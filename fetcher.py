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
import unicodedata
import urllib.request
from bs4 import BeautifulSoup, Comment

# Invisible / format code points attackers use to smuggle instructions past a
# CSS-based "is it visible?" check: zero-width chars, BOM, soft hyphen, and the
# Unicode Tags block (U+E0000..U+E007F) that mirrors ASCII invisibly.
_ZERO_WIDTH = "​‌‍⁠﻿­"


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode("utf-8", "replace")


def _strip_invisible_unicode(text: str) -> str:
    """Drop code points a human can never see but a model still reads."""
    out = []
    for ch in text:
        if ch in _ZERO_WIDTH:
            continue
        if 0xE0000 <= ord(ch) <= 0xE007F:      # Unicode Tags block
            continue
        if unicodedata.category(ch) == "Cf":   # other format chars
            continue
        out.append(ch)
    return "".join(out)


def extract_text_naive(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # keeps comments, hidden divs, invisible text -- everything as raw text
    text = soup.get_text(separator=" ")
    comments = soup.find_all(string=lambda t: isinstance(t, Comment))
    text += " " + " ".join(c for c in comments)
    # a careless scraper also slurps attribute text (alt/title/aria-label/meta),
    # which get_text() alone never returns -- another channel for hidden commands
    for tag in soup.find_all(True):
        for attr in ("alt", "title", "aria-label"):
            if tag.get(attr):
                text += " " + tag[attr]
        if tag.name == "meta" and tag.get("content"):
            text += " " + tag["content"]
    return re.sub(r"\s+", " ", text).strip()


def _is_hidden(tag) -> bool:
    """Heuristic 'a human can't see this' check across many hiding techniques.

    Real defenses need a real renderer; this catches the common CSS tricks so
    students can see which technique each defense layer stops.
    """
    style = (tag.get("style") or "").lower().replace(" ", "")

    # 1. removed from layout / not painted
    if "display:none" in style or "visibility:hidden" in style:
        return True
    # 2. fully transparent
    if "opacity:0" in style or "opacity:.0" in style or "opacity:0.0" in style:
        return True
    # 3. zero / near-zero font size
    if re.search(r"font-size:0(px|pt|em|rem|%|;|$)", style):
        return True
    # 4. pushed off-screen
    if ("position:absolute" in style or "position:fixed" in style) and \
       re.search(r"(left|top|right|bottom):-\d{3,}", style):
        return True
    if re.search(r"text-indent:-\d{3,}", style) or "left:-9999" in style:
        return True
    # 5. white-on-white (accept #fff, #ffffff, and the word 'white')
    white = ("color:#fff" in style or "color:#ffffff" in style or "color:white" in style)
    whitebg = ("background:#fff" in style or "background:#ffffff" in style or
               "background:white" in style or "background-color:#fff" in style or
               "background-color:#ffffff" in style or "background-color:white" in style)
    if white and whitebg:
        return True
    # 6. class-based hiding used in the demo pages
    cls = " ".join(tag.get("class", [])).lower()
    return any(h in cls for h in ("invisible", "hidden", "sr-only", "visually-hidden"))


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
    # Also drop invisible Unicode (zero-width + Tags block) that no CSS check
    # would catch but a model would still obey.
    text = _strip_invisible_unicode(soup.get_text(separator=" "))
    return re.sub(r"\s+", " ", text).strip()
