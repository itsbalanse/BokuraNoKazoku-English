"""Write translated EVENT .mes files to build/mod/EVENT.XAP using tl/events chunk translations.

Each translated page is written as one physical line ("\\t<line1>@n<line2>@n...") and pages are
separated by "\\t," lines, keeping the label line (and its voice timings) untouched.
Reports pages that exceed MAX_LINES lines or byte limits.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textfit
from events_extract import SRC, BLOCK_RE, body_of, pages_of, load_existing, W

OUT = os.path.join(W, "build", "mod", "EVENT.XAP")
MAX_LINES = 3
MAX_PX = float(os.environ.get("EVENT_MAX_PX", "460"))


def render_page(en):
    lines = textfit.wrap(textfit.sanitize(en), MAX_PX)
    return lines


def main():
    tr = load_existing()
    index = json.load(open(os.path.join(W, "tl", "events_index.json"), encoding="utf-8"))
    by_body = {v["jp"]: k for k, v in index.items()}
    os.makedirs(OUT, exist_ok=True)
    problems = []
    written = blocks = done = 0
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".mes"):
            continue
        t = open(os.path.join(SRC, f), "rb").read().decode("cp932")
        out = []
        pos = 0
        changed = False
        for m in BLOCK_RE.finditer(t):
            blocks += 1
            lines = [l[1:].rstrip("\r") for l in m.group(3).split("\n") if l.startswith("\t")]
            body = body_of(lines)
            bid = by_body.get(body)
            en = tr.get(bid) if bid else None
            if not en:
                continue
            jp_pages = pages_of(body)
            en_pages = [p.strip() for p in en.split("||")]
            if len(en_pages) != len(jp_pages):
                problems.append(f"{bid} {f} {m.group(1)}: {len(en_pages)} EN pages vs {len(jp_pages)} JP")
                continue
            phys = []
            for i, p in enumerate(en_pages):
                ls = render_page(p)
                if len(ls) > MAX_LINES:
                    problems.append(f"{bid} {f} {m.group(1)} page {i + 1}: {len(ls)} lines: {ls}")
                line = textfit.lead_safe(textfit.join_lines(ls) + "@n")
                if len(line.encode("cp932")) > 250:
                    problems.append(f"{bid} {f} {m.group(1)} page {i + 1}: line too long in bytes")
                if i:
                    phys.append("\t,")
                phys.append("\t" + line)
            newbody = "\r\n".join(phys) + "\r\n"
            nb = len("".join(phys).encode("cp932"))
            if nb > 960:
                problems.append(f"{bid} {f} {m.group(1)}: body {nb} bytes, limit 1024")
            s3, e3 = m.span(3)
            out.append(t[pos:s3])
            out.append(newbody)
            pos = e3
            changed = True
            done += 1
        if changed:
            out.append(t[pos:])
            open(os.path.join(OUT, f), "wb").write("".join(out).encode("cp932"))
            written += 1
        elif os.path.exists(os.path.join(OUT, f)):
            os.remove(os.path.join(OUT, f))
    print(f"translated blocks written: {done}/{blocks} in {written} files; problems: {len(problems)}")
    for p in problems:
        print("  " + p)


if __name__ == "__main__":
    main()
