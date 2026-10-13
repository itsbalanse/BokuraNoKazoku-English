"""Create a BPS patch (original ISO -> translated ISO) that carries only new data.

Unchanged sectors become SourceRead; inside changed files, any 16-byte-aligned run that also
exists in the ORIGINAL version of that file (archive entries that were only shifted) becomes
SourceCopy, so original game data is referenced from the player's own disc rather than shipped.
Only genuinely new bytes (translated text, repainted textures, recompressed entries, the
patched executable code) are stored as TargetRead.

usage: mkpatch.py ORIGINAL.iso PATCHED.iso OUT.bps
"""
import os, sys, zlib, struct

sys.path.insert(0, os.path.dirname(__file__))
import iso9660

SECTOR = 2048
BLOCK = 32          # match key length
ALIGN = 16          # XAP entries are 16-byte aligned
MIN_MATCH = 64


def vint(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


class Writer:
    def __init__(self, src_size, tgt_size, meta=b""):
        self.buf = bytearray(b"BPS1" + vint(src_size) + vint(tgt_size) + vint(len(meta)) + meta)
        self.out = 0          # output (target) position
        self.src_rel = 0      # SourceCopy relative offset
        self.literal = 0
        self.copied = 0

    def source_read(self, n):
        while n:
            k = min(n, 1 << 30)
            self.buf += vint(((k - 1) << 2) | 0)
            self.out += k
            n -= k

    def target_read(self, data):
        if data:
            self.buf += vint(((len(data) - 1) << 2) | 1) + data
            self.out += len(data)
            self.literal += len(data)

    def source_copy(self, src_off, n):
        d = src_off - self.src_rel
        self.buf += vint(((n - 1) << 2) | 2) + vint((abs(d) << 1) | (1 if d < 0 else 0))
        self.src_rel = src_off + n
        self.out += n
        self.copied += n


def changed_spans(fs, ft, size, chunk=1 << 24):
    """Yield (start, end) byte spans (sector aligned) where the images differ."""
    pos, cur = 0, None
    while pos < size:
        fs.seek(pos); ft.seek(pos)
        a, b = fs.read(chunk), ft.read(chunk)
        if a != b:
            for s in range(0, len(a), SECTOR):
                if a[s:s + SECTOR] != b[s:s + SECTOR]:
                    p = pos + s
                    if cur and p <= cur[1]:
                        cur[1] = p + SECTOR
                    else:
                        if cur:
                            yield tuple(cur)
                        cur = [p, p + SECTOR]
        pos += chunk
    if cur:
        yield tuple(cur)


def main(src_path, tgt_path, out_path):
    ssize, tsize = os.path.getsize(src_path), os.path.getsize(tgt_path)
    fs, ft = open(src_path, "rb"), open(tgt_path, "rb")
    _, srecs = iso9660.walk(fs)
    files = sorted((r.lba * SECTOR, r.lba * SECTOR + ((r.size + SECTOR - 1) // SECTOR) * SECTOR, r.path)
                   for r in srecs if not r.is_dir)

    _, trecs = iso9660.walk(ft)
    by_path = {r.path: r for r in srecs if not r.is_dir}
    moved = [(r.lba * SECTOR, r.lba * SECTOR + ((r.size + SECTOR - 1) // SECTOR) * SECTOR, r.path)
             for r in trecs if not r.is_dir and r.path in by_path and by_path[r.path].lba != r.lba]

    def owner(start, end):
        # a file the build relocated: match against that file's ORIGINAL location
        for a, b, p in moved:
            if a < end and b > start:
                o = by_path[p]
                return o.lba * SECTOR, o.lba * SECTOR + o.size, p + " (relocated)"
        """Original-file byte window covering a changed span (whole file, else the span)."""
        hit = [(a, b, p) for a, b, p in files if a < end and b > start]
        if not hit:
            return start, end, "(system area / directories)"
        return (min([start] + [a for a, _, _ in hit]), max([end] + [b for _, b, _ in hit]),
                " + ".join(p for _, _, p in hit))

    # merge spans belonging to the same file
    spans = []
    for s, e in changed_spans(fs, ft, min(ssize, tsize)):
        lo, hi, p = owner(s, e)
        if spans and spans[-1][2] == p:
            spans[-1][1] = e
        else:
            spans.append([s, e, p, lo, hi])
    if tsize > ssize:
        spans.append([ssize, tsize, "(appended)", ssize, ssize])

    w = Writer(ssize, tsize, b"Bokura no Kazoku English translation")
    for s, e, p, lo, hi in spans:
        w.source_read(s - w.out)
        fs.seek(lo); window = fs.read(hi - lo)
        index = {}
        for i in range(0, len(window) - BLOCK, ALIGN):
            index.setdefault(window[i:i + BLOCK], i)
        ft.seek(s); data = ft.read(e - s)
        i, lit = 0, bytearray()
        while i < len(data):
            j = index.get(data[i:i + BLOCK]) if i % ALIGN == 0 else None
            if j is not None:
                n = BLOCK
                while i + n < len(data) and j + n < len(window) and data[i + n] == window[j + n]:
                    n += 1
                if n >= MIN_MATCH:
                    w.target_read(bytes(lit)); lit.clear()
                    w.source_copy(lo + j, n)
                    i += n
                    continue
            lit.append(data[i]); i += 1
        w.target_read(bytes(lit))
        print(f"  {p:28s} {e - s:>10,} bytes changed region")
    w.source_read(tsize - w.out)

    def crc(f):
        f.seek(0); c = 0
        while b := f.read(1 << 24):
            c = zlib.crc32(b, c)
        return c
    w.buf += struct.pack("<II", crc(fs), crc(ft))
    w.buf += struct.pack("<I", zlib.crc32(w.buf))
    open(out_path, "wb").write(w.buf)
    print(f"patch {len(w.buf):,} bytes; new data {w.literal:,}; referenced from original {w.copied:,}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
