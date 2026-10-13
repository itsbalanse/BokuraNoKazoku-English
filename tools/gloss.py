"""Generate <SUB> mapping lines for whole-field glossary terms in a data file.

usage: gloss.py GLOSSARY.tsv REL [REL...]   -> appends to tl/txt/REL.tsv (dedup) and reports misses
A term matches only as a complete CSV-ish field: preceded by start/','/tab/space and followed by
','/tab/end/space/'#', so 'ABC' never matches inside 'ABCD'.
"""
import os, re, sys

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(W, "extracted", "DATA")
TL = os.path.join(W, "tl", "txt")


def load_gloss(path):
    g = {}
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if "\t" in line and not line.startswith("//"):
            k, v = line.split("\t", 1)
            g[k] = v
    return g


def main(gpath, rels):
    g = load_gloss(gpath)
    used = set()
    for rel in rels:
        lines = open(os.path.join(SRC, rel), "rb").read().decode("cp932").split("\r\n")
        out = []
        for i, l in enumerate(lines, 1):
            body = l.split("#")[0]
            for k in sorted(g, key=len, reverse=True):
                pat = r"(?:(?<=^)|(?<=[,\t =]))" + re.escape(k) + r"(?=\s*(?:,|$|\t|#|\"))"
                while re.search(pat, body):
                    out.append(f"{i}\t<SUB>\t{k}\t{g[k]}")
                    used.add(k)
                    body = re.sub(pat, "\x00", body, count=1)
        tsv = os.path.join(TL, rel + ".tsv")
        os.makedirs(os.path.dirname(tsv), exist_ok=True)
        existing = open(tsv, encoding="utf-8").read().splitlines() if os.path.exists(tsv) else []
        merged = existing + [o for o in out if o not in existing]
        open(tsv, "w", encoding="utf-8").write("\n".join(merged) + "\n")
        print(f"{rel}: {len(out)} substitutions")
    unused = [k for k in g if k not in used]
    if unused:
        print("unused glossary terms:", unused)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
