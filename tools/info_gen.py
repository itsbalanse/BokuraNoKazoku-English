"""Build tl/txt mapping files for MENU.XAP *info.txt description fields from English sources.

Source: tl/info/<file>.tsv, lines "ID<TAB>description[<TAB>condition]".
  {text} = highlighted (the game's accent colour), wrapped to the info box at a small size.
The ID matches the leading number field of the data line; the texture field is preserved.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textfit

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "@r115@g115@b115"
HI = "@r92@g87@b42"
SIZE = 14
MAX_PX = 212.0
MAX_LINES = 4


def render(text, size=SIZE, max_px=MAX_PX, max_lines=MAX_LINES, ident=""):
    """Greedy word wrap measured without {} markers; markers become colour codes in place."""
    tokens = textfit.sanitize(text).split()
    lines, cur = [], []
    for t in tokens:
        cand = " ".join(cur + [t]).replace("{", "").replace("}", "")
        if cur and textfit.width(cand, size) > max_px:
            lines.append(cur)
            cur = [t]
        else:
            cur.append(t)
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        print(f"  WARN {ident}: {len(lines)} lines")
    rendered = [" ".join(l).replace("{", HI).replace("}", BASE) for l in lines]
    return f"@s{size}{BASE}" + textfit.join_lines(rendered)


def gen(name, cond_size=None):
    src = os.path.join(W, "tl", "info", name + ".tsv")
    rel = f"MENU.XAP/{name}.txt"
    orig = open(os.path.join(W, "extracted", "DATA", rel), "rb").read().decode("cp932").split("\r\n")
    tr = {}
    for line in open(src, encoding="utf-8"):
        line = line.rstrip("\n")
        if line and not line.startswith("//"):
            parts = line.split("\t")
            tr[parts[0]] = parts[1:]
    out = []
    for i, l in enumerate(orig, 1):
        m = re.match(r"^(\s*)(\d+)(\s*,\s*)([^,]*?)(\s*,\s*)(.*)$", l)
        if not m or m.group(2) not in tr:
            continue
        parts = tr[m.group(2)]
        desc = render(parts[0], ident=f"{name}:{m.group(2)}")
        new = f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{m.group(5)}{desc}"
        if len(parts) > 1:
            new += "," + f"@s{cond_size or 15}{BASE}" + textfit.sanitize(parts[1])
        out.append(f"{i}\t{new}")
    dst = os.path.join(W, "tl", "txt", rel + ".tsv")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(f"{rel}: {len(out)} lines generated")


if __name__ == "__main__":
    for n in sys.argv[1:]:
        gen(n)
