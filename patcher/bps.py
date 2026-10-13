"""Minimal streaming BPS patcher (handles multi-GB disc images).

usage: bps.py PATCH.bps ORIGINAL.iso OUTPUT.iso
"""
import sys, zlib, struct, os


def apply(patch_path, src_path, out_path, progress=print):
    p = open(patch_path, "rb").read()
    if p[:4] != b"BPS1":
        raise ValueError("not a BPS patch")
    if zlib.crc32(p[:-4]) != struct.unpack("<I", p[-4:])[0]:
        raise ValueError("patch file is corrupt")
    src_crc, tgt_crc = struct.unpack("<II", p[-12:-4])
    pos = 4

    def vint():
        nonlocal pos
        data, shift = 0, 1
        while True:
            x = p[pos]; pos += 1
            data += (x & 0x7F) * shift
            if x & 0x80:
                return data
            shift <<= 7
            data += shift

    ssize, tsize, msize = vint(), vint(), vint()
    pos += msize
    if os.path.getsize(src_path) != ssize:
        raise ValueError("wrong source file size: this is not the expected game image")
    progress("checking your ISO...")
    c = 0
    with open(src_path, "rb") as f:
        while b := f.read(1 << 24):
            c = zlib.crc32(b, c)
    if c != src_crc:
        raise ValueError(f"source CRC32 {c:08x} does not match {src_crc:08x}: "
                         "use the Redump dump of Bokura no Kazoku (SCPS-15088)")
    src = open(src_path, "rb")
    out = open(out_path, "w+b")
    opos, src_rel, tgt_rel, tc = 0, 0, 0, 0
    end = len(p) - 12
    last = 0
    while pos < end:
        d = vint(); cmd, n = d & 3, (d >> 2) + 1
        if cmd == 0:      # SourceRead
            src.seek(opos)
            left = n
            while left:
                b = src.read(min(left, 1 << 24)); out.write(b); tc = zlib.crc32(b, tc); left -= len(b)
        elif cmd == 1:    # TargetRead
            b = p[pos:pos + n]; pos += n; out.write(b); tc = zlib.crc32(b, tc)
        elif cmd == 2:    # SourceCopy
            o = vint(); src_rel += (-1 if o & 1 else 1) * (o >> 1)
            src.seek(src_rel); b = src.read(n); src_rel += n
            out.write(b); tc = zlib.crc32(b, tc)
        else:             # TargetCopy
            o = vint(); tgt_rel += (-1 if o & 1 else 1) * (o >> 1)
            for _ in range(n):
                out.seek(tgt_rel); x = out.read(1); out.seek(opos)
                out.write(x); tc = zlib.crc32(x, tc); tgt_rel += 1; opos += 1
            continue
        opos += n
        if opos - last > 200 << 20:
            last = opos
            progress(f"{opos * 100 // tsize}%")
    out.close()
    if opos != tsize or tc != tgt_crc:
        os.remove(out_path)
        raise ValueError("output check failed")
    progress("done - output verified")


if __name__ == "__main__":
    apply(*sys.argv[1:4])
