"""Make an analysis-only copy of a PS2 EE ELF that generic MIPS64 tools can decode:
lq -> ld, sq -> sd (same operand layout). Also reports how many were rewritten.
The ELF header's e_flags/machine are left alone; import with an explicit language."""
import struct, sys

src, dst = sys.argv[1], sys.argv[2]
b = bytearray(open(src, "rb").read())
phoff = struct.unpack_from("<I", b, 0x1C)[0]
n = struct.unpack_from("<H", b, 0x2C)[0]
cnt = {0x1E: 0, 0x1F: 0}
for i in range(n):
    t, off, va, pa, fs, ms, fl, al = struct.unpack_from("<8I", b, phoff + i * 32)
    if t != 1 or not (fl & 1):
        continue
    for o in range(off, off + fs, 4):
        w = struct.unpack_from("<I", b, o)[0]
        op = w >> 26
        if op == 0x1E:  # lq
            w = (w & 0x03FFFFFF) | (0x37 << 26)
            cnt[0x1E] += 1
        elif op == 0x1F:  # sq
            w = (w & 0x03FFFFFF) | (0x3F << 26)
            cnt[0x1F] += 1
        else:
            continue
        struct.pack_into("<I", b, o, w)
open(dst, "wb").write(b)
print("lq->ld", cnt[0x1E], "sq->sd", cnt[0x1F])
