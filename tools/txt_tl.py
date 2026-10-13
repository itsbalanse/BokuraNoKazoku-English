"""Line-level translation of the game's .txt/.mes data files.

  txt_tl.py show REL [--all]     print lines containing Japanese (outside # comments) with numbers
  txt_tl.py apply                apply every tl/txt/**/*.tsv to build/mod/

Mapping files: tl/txt/<REL>.tsv, e.g. tl/txt/MENURES.XAP/menumes.txt.tsv, lines:
    <lineno><TAB><replacement line>      (lineno is 1-based, as printed by `show`)
    <lineno><TAB><DEL>                   remove the line (used when joining multi-line entries)
    <lineno><TAB><SUB><TAB><old><TAB><new>   replace a substring of the line (may repeat per line)
Replacement text is written as-is (CP932, CRLF); full-width '，' must be used for commas inside
text fields because ASCII ',' is a field/page separator in these formats.
"""
import os, re, sys

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(W, "extracted", "DATA")
TL = os.path.join(W, "tl", "txt")
OUT = os.path.join(W, "build", "mod")
JP = re.compile(r"[぀-ヿ一-鿿！-～、-〿]")


def read(rel):
    return open(os.path.join(SRC, rel), "rb").read().decode("cp932").split("\r\n")


def show(rel, all_lines=False):
    for i, l in enumerate(read(rel), 1):
        body = l.split("#")[0]
        if all_lines or JP.search(body):
            print(f"{i}\t{l}")


def apply():
    n_files = 0
    for r, d, fs in os.walk(TL):
        for f in fs:
            if not f.endswith(".tsv"):
                continue
            rel = os.path.relpath(os.path.join(r, f), TL)[:-4]
            lines = read(rel)
            mapping = {}
            for raw in open(os.path.join(r, f), encoding="utf-8"):
                raw = raw.rstrip("\n").rstrip("\r")
                if not raw or raw.startswith("//"):
                    continue
                num, _, text = raw.partition("\t")
                if text.startswith("<SUB>\t"):
                    # substring substitution inside the original (or already mapped) line
                    _, old, new = text.split("\t", 2)
                    cur = mapping.get(int(num), lines[int(num) - 1])
                    if old not in cur:
                        raise SystemExit(f"{rel}:{num}: '{old}' not found in: {cur}")
                    mapping[int(num)] = cur.replace(old, new, 1)
                    continue
                mapping[int(num)] = text
            out = []
            for i, l in enumerate(lines, 1):
                if i in mapping:
                    if mapping[i] == "<DEL>":
                        continue
                    out.append(mapping[i])
                else:
                    out.append(l)
            data = "\r\n".join(out)
            try:
                enc = data.encode("cp932")
            except UnicodeEncodeError as e:
                raise SystemExit(f"{rel}: cannot encode: {e}")
            dst = os.path.join(OUT, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(enc)
            n_files += 1
            left = [i for i, l in enumerate(out, 1) if JP.search(l.split("#")[0])]
            print(f"{rel}: {len(mapping)} lines mapped; JP lines left: {len(left)}")
    # whole-file replacements: tl/txt/<REL>.full (UTF-8, written as CP932 + CRLF)
    for r, d, fs in os.walk(TL):
        for f in fs:
            if f.endswith(".full"):
                rel = os.path.relpath(os.path.join(r, f), TL)[:-5]
                text = open(os.path.join(r, f), encoding="utf-8").read().replace("\r\n", "\n")
                dst = os.path.join(OUT, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, "wb").write(text.replace("\n", "\r\n").encode("cp932"))
                n_files += 1
                print(f"{rel}: full replacement")
    print(f"applied {n_files} files")


if __name__ == "__main__":
    if sys.argv[1] == "show":
        show(sys.argv[2], "--all" in sys.argv)
    else:
        apply()
