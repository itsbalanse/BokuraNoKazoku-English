"""Shared English text sanitizing + pixel-width wrapping for the game's font (font20.moj).

Width model (calibrated against in-game screenshots): advance = ink width + 0.75 px, space 4.7 px,
at the default size 20. $VAR$ names are budgeted at VAR_PX.
"""
import os, re, unicodedata

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moji

GLYPHS = moji.load(os.path.join(W, "font", "font20.moj"))
VAR_PX = 100.0
SPACE_PX = 4.7
GAP_PX = 0.75

REPL = {
    "‘": "'", "’": "'", "“": '"', "”": '"', "—": "-", "–": "-",
    "…": "...", "é": "e", "è": "e", "à": "a", "ü": "u", "ö": "o",
    " ": " ", "#": "No.", "　": " ",
}


def sanitize(s):
    """Map to characters the game font/parser accept. ASCII comma -> full-width comma."""
    for k, v in REPL.items():
        s = s.replace(k, v)
    s = s.replace(",", "，")
    out = []
    for ch in s:
        try:
            ch.encode("cp932")
            out.append(ch)
        except UnicodeEncodeError:
            n = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()
            out.append(n or "?")
    return "".join(out)


TOKEN = re.compile(r"\$[A-Za-z_]+\$|@[a-z]-?\d*|.", re.S)


def width(s, size=20):
    w = 0.0
    for t in TOKEN.findall(s):
        if t.startswith("$") and len(t) > 1:
            w += VAR_PX
        elif t.startswith("@") and len(t) > 1:
            continue
        elif t == " ":
            w += SPACE_PX
        else:
            b = t.encode("cp932", "replace")
            code = b[0] if len(b) == 1 else (b[0] << 8 | b[1])
            g = GLYPHS.get(code)
            w += (g[2] if g else 20) + GAP_PX
    return w * size / 20.0


def wrap(text, max_px=460.0, size=20, balance=True):
    """Wrap to max_px; with balance, use the narrowest width that keeps the same line count
    (centered subtitles look better with even lines)."""
    lines = _greedy(text, max_px, size)
    if not balance or len(lines) < 2:
        return lines
    lo, hi = 1.0, max_px
    best = lines
    for _ in range(14):
        mid = (lo + hi) / 2
        cand = _greedy(text, mid, size)
        if len(cand) <= len(lines) and all(width(l, size) <= mid or " " not in l for l in cand):
            best, hi = cand, mid
        else:
            lo = mid
    return best


def _greedy(text, max_px, size=20):
    """Greedy wrap on spaces; '\\' forces a break. Returns list of lines."""
    lines = []
    for para in text.split("\\"):
        words = para.strip().split(" ")
        cur = ""
        for wd in words:
            if not wd:
                continue
            cand = wd if not cur else cur + " " + wd
            if cur and width(cand, size) > max_px:
                lines.append(cur)
                cur = wd
            else:
                cur = cand
        lines.append(cur)
    return [l for l in lines if l != ""] or [""]


def lead_safe(s):
    """The .mes/.txt line reader treats a line starting with [0-9A-Za-z] as a label: prefix @d0."""
    if s[:1].isascii() and s[:1].isdigit():
        return "@d0 " + s
    return "@d0" + s if s[:1].isascii() and s[:1].isalpha() else s


def join_lines(lines):
    """Join with @n; a line starting with a digit gets a space so the digit isn't read as an @n argument."""
    out = ""
    for i, l in enumerate(lines):
        if i:
            out += "@n" + (" " if l[:1].isdigit() else "")
        out += l
    return out
