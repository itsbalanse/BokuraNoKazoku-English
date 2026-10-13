import struct, sys

a = open(sys.argv[1], "rb").read()
b = open(sys.argv[2], "rb").read()
print("sizes", len(a), len(b))
phoff = struct.unpack_from("<I", a, 0x1C)[0]
n = struct.unpack_from("<H", a, 0x2C)[0]
segs = []
for i in range(n):
    t, off, va, pa, fs, ms, fl, al = struct.unpack_from("<8I", a, phoff + i * 32)
    segs.append((off, va, fs, ms))
    print("PH", i, hex(t), "off", hex(off), "va", hex(va), "filesz", hex(fs), "memsz", hex(ms), "flags", fl)
print("entry", hex(struct.unpack_from("<I", a, 0x18)[0]))


def va(o):
    for off, v, fs, ms in segs:
        if off <= o < off + fs:
            return v + o - off
    return 0


diffs = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
runs = []
for i in diffs:
    if runs and i - runs[-1][1] <= 8:
        runs[-1][1] = i + 1
    else:
        runs.append([i, i + 1])
print("runs", len(runs), "bytes differing", len(diffs))
for s, e in runs:
    print(f"file {s:#08x} va {va(s):#010x} len {e - s}")
