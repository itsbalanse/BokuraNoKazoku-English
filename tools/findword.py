"""Find 32-bit words (e.g. function pointers in vtables) and jal call sites in a PS2 ELF.
usage: findword.py ELF HEXADDR..."""
import struct, sys

b = open(sys.argv[1], "rb").read()
phoff = struct.unpack_from("<I", b, 0x1C)[0]
n = struct.unpack_from("<H", b, 0x2C)[0]
segs = []
for i in range(n):
    t, off, va, pa, fs, ms, fl, al = struct.unpack_from("<8I", b, phoff + i * 32)
    if t == 1:
        segs.append((off, va, fs, fl))
for h in sys.argv[2:]:
    target = int(h, 16)
    jal = (3 << 26) | (target >> 2)
    for off, va, fs, fl in segs:
        for o in range(off, off + fs - 3, 4):
            w = struct.unpack_from("<I", b, o)[0]
            if w == target:
                print(f"{h}: word at {va + o - off:08x}")
            elif w == jal:
                print(f"{h}: jal at   {va + o - off:08x}")
