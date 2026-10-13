"""List ASCII and Shift-JIS strings in the PS2 ELF with their virtual addresses."""
import re, struct, sys

a = open(sys.argv[1], "rb").read()
mode = sys.argv[2] if len(sys.argv) > 2 else "all"
phoff = struct.unpack_from("<I", a, 0x1C)[0]
n = struct.unpack_from("<H", a, 0x2C)[0]
segs = []
for i in range(n):
    t, off, va, pa, fs, ms, fl, al = struct.unpack_from("<8I", a, phoff + i * 32)
    if t == 1:
        segs.append((off, va, fs))


def va(o):
    for off, v, fs in segs:
        if off <= o < off + fs:
            return v + o - off
    return 0


sj = re.compile(rb"(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]|[\x20-\x7e]){3,}\x00")
for m in sj.finditer(a):
    s = m.group()[:-1]
    has_jp = re.search(rb"[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]", s) is not None
    if mode == "jp" and not has_jp:
        continue
    if mode == "ascii" and has_jp:
        continue
    try:
        t = s.decode("cp932")
    except UnicodeDecodeError:
        continue
    if mode == "jp" and not re.search(r"[぀-ヿ一-鿿＀-￯]", t):
        continue
    print(f"{va(m.start()):08x} {m.start():07x} {t}")
