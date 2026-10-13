"""Extract unique dialogue blocks from EVENT.XAP .mes files into translation chunk files.

Chunk record format (UTF-8):
    @@ <id> | <file> <label> [+N more] | pages=<n>
    JP: <page1> ¦ <page2> ...
    EN: <english page1> || <english page2> ...

EN rules: no @n needed (auto-wrapped); '\\' forces a line break; '||' separates pages and the page
count must match JP; $OTO$ etc. stay as-is. Existing EN lines in chunk files are preserved on re-run.
"""
import json, os, re, sys

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(W, "extracted", "DATA", "EVENT.XAP")
OUT = os.path.join(W, "tl", "events")
CHUNK = 120

BLOCK_RE = re.compile(r"^([0-9a-z]{6}_\d+)((?:, *[\d.]+)*)\r?\n((?:\t.*(?:\r?\n|$))+)", re.M)


def parse_mes(text):
    """Yield (label, timing_suffix, body_lines, span)."""
    for m in BLOCK_RE.finditer(text):
        lines = [l[1:].rstrip("\r") for l in m.group(3).split("\n") if l.startswith("\t")]
        yield m.group(1), m.group(2), lines, m.span()


def body_of(lines):
    return "".join(l.strip(" \t") for l in lines)


def pages_of(body):
    return [p.strip(" \t") for p in body.split(",")]


def load_existing():
    """EN text from chunk files' EN: lines, overridden by tl/events/en/*.txt ("id<TAB>text")."""
    tr = {}
    if not os.path.isdir(OUT):
        return tr
    en_dir = os.path.join(OUT, "en")
    if os.path.isdir(en_dir):
        for f in sorted(os.listdir(en_dir)):
            for line in open(os.path.join(en_dir, f), encoding="utf-8"):
                line = line.rstrip("\n")
                if "\t" in line and line[:4].isdigit():
                    bid, text = line.split("\t", 1)
                    if text.strip():
                        tr.setdefault(bid.strip(), text.strip())
        if tr:
            return tr
    for f in sorted(os.listdir(OUT)):
        if not f.endswith(".txt"):
            continue
        cur = None
        for line in open(os.path.join(OUT, f), encoding="utf-8"):
            line = line.rstrip("\n")
            if line.startswith("@@ "):
                cur = line.split("|")[0][3:].strip()
            elif line.startswith("EN:") and cur:
                en = line[3:].strip()
                if en:
                    tr[cur] = en
    return tr


def main():
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".mes"))
    uniq = {}  # body -> id
    order = []
    occ = {}
    for f in files:
        t = open(os.path.join(SRC, f), "rb").read().decode("cp932")
        for label, timing, lines, span in parse_mes(t):
            body = body_of(lines)
            if body not in uniq:
                bid = f"{len(uniq) + 1:04d}"
                uniq[body] = bid
                order.append(body)
                occ[bid] = []
            occ[uniq[body]].append([f, label])
    existing = load_existing()
    os.makedirs(OUT, exist_ok=True)
    index = {}
    for ci in range(0, len(order), CHUNK):
        part = order[ci: ci + CHUNK]
        path = os.path.join(OUT, f"chunk_{ci // CHUNK + 1:02d}.txt")
        with open(path, "w", encoding="utf-8", newline="\n") as fo:
            last_file = None
            for body in part:
                bid = uniq[body]
                o = occ[bid]
                if o[0][0] != last_file:
                    fo.write(f"\n### {o[0][0]}\n")
                    last_file = o[0][0]
                more = f" +{len(o) - 1} more" if len(o) > 1 else ""
                pg = pages_of(body)
                fo.write(f"@@ {bid} | {o[0][0]} {o[0][1]}{more} | pages={len(pg)}\n")
                fo.write("JP: " + " ¦ ".join(pg) + "\n")
                fo.write("EN: " + existing.get(bid, "") + "\n")
        for body in part:
            index[uniq[body]] = {"jp": body, "occ": occ[uniq[body]]}
    json.dump(index, open(os.path.join(W, "tl", "events_index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    done = sum(1 for b in index if b in existing)
    print(f"{len(order)} unique blocks in {(len(order) + CHUNK - 1) // CHUNK} chunks; translated {done}")


if __name__ == "__main__":
    main()
