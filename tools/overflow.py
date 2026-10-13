"""Overflow audit: compare the rendered width of every translated UI string with the Japanese
string it replaced (same font-size codes, same base size). Layouts were sized for the Japanese,
so English that is clearly wider is a candidate overflow.

  overflow.py [REL ...]        default: every file under build/mod that has a .tsv/.full mapping
Prints: excess_px  en_px  jp_px  file:line[field]  text
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
from textfit import GLYPHS, SPACE_PX, GAP_PX, VAR_PX

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(W, "extracted", "DATA")
MOD = os.path.join(W, "build", "mod")
TOK = re.compile(r"\$[A-Za-z_]+\$|@[a-z]-?\d*|%\d*[sd]|.", re.S)


def lines_width(s, size=18.0):
    """Max rendered line width (px at 640 wide) honouring @sN size changes, @dN offsets, @n breaks."""
    best = cur = 0.0
    for t in TOK.findall(s):
        if t == "@n":
            best, cur = max(best, cur), 0.0
        elif t.startswith("@s") and len(t) > 2:
            size = float(t[2:])
        elif t.startswith("@d") and len(t) > 2:
            cur += float(t[2:])
        elif t.startswith("@") and len(t) > 1:
            continue
        elif t.startswith("$") and len(t) > 1:
            cur += VAR_PX * size / 20
        elif t.startswith("%"):
            cur += 60 * size / 20          # unknown inserted value
        elif t == " ":
            cur += SPACE_PX * size / 20
        else:
            b = t.encode("cp932", "replace")
            code = b[0] if len(b) == 1 else (b[0] << 8 | b[1])
            g = GLYPHS.get(code)
            cur += ((g[2] if g else 20) + GAP_PX) * size / 20
    return max(best, cur)


def fields(line):
    """Comparable text pieces of one line: quoted strings, else CSV-ish fields, else the line."""
    body = line.split("#")[0] if not line.lstrip().startswith("#") else ""
    q = re.findall(r'"([^"]*)"', body)
    if q:
        return q
    if "\t" in body.strip() and re.match(r"^\d{3}\t", body.strip()):
        return [body.strip().split("\t", 1)[1]]
    return [f.strip() for f in body.split(",")]


def audit(rel):
    try:
        jp = open(os.path.join(SRC, rel), "rb").read().decode("cp932").split("\r\n")
        en = open(os.path.join(MOD, rel), "rb").read().decode("cp932").split("\r\n")
    except FileNotFoundError:
        return []
    out = []
    if len(jp) != len(en):
        return [(0, 0, 0, rel, 0, "(line count differs - skipped)")]
    for i, (a, b) in enumerate(zip(jp, en), 1):
        if a == b:
            continue
        fa, fb = fields(a), fields(b)
        if len(fa) != len(fb):
            fa, fb = [a], [b]
        for k, (x, y) in enumerate(zip(fa, fb)):
            if x == y:
                continue
            wj, we = lines_width(x), lines_width(y)
            if we > wj + 6 and we > 30:
                out.append((we - wj, we, wj, rel, f"{i}[{k}]", y))
    return out


def mapped():
    tl = os.path.join(W, "tl", "txt")
    for r, d, fs in os.walk(tl):
        for f in fs:
            if f.endswith(".tsv"):
                yield os.path.relpath(os.path.join(r, f), tl)[:-4]
            elif f.endswith(".full"):
                yield os.path.relpath(os.path.join(r, f), tl)[:-5]


if __name__ == "__main__":
    rels = sys.argv[1:] or sorted(set(mapped()))
    rows = []
    for rel in rels:
        rows += audit(rel)
    rows.sort(key=lambda r: (r[3], -r[0]))
    for ex, we, wj, rel, where, text in rows:
        print(f"{ex:6.0f} {we:6.0f} {wj:6.0f}  {rel}:{where}  {text[:110]}")
    print(len(rows), "candidates")
