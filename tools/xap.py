"""XAP archive reader/writer for Bokura no Kazoku (SCPS-15088).

Format (reverse engineered from xapep.exe with REA/Ghidra and verified against the disc):

  0x00  "XAPF"  u32 (file_size - 0x10)  u32 file_chunk_size  u32 body_chunk_size
  0x10  "FILE"  u32 (file_chunk_size - 8)  u32 version(=1)  u32 count
  0x20  count * 32-byte entries:
          u32 name_offset (relative to 0x18, i.e. FILE chunk payload)
          u32 flags        (1 = LZ compressed, 0 = stored)
          u32 data_offset  (absolute in file)
          u32 raw_size
          u32 stored_size
          u32 dos_date_time
          u32 extra        (opaque, kept verbatim)
          u32 zero
        followed by NUL-terminated names, padding
  0x10 + file_chunk_size: "BODY" u32 (body_chunk_size - 8), 8 bytes pad, then data
  (each entry 16-byte aligned; file ends 16-byte aligned)

Compression: LZ77 with an MSB-first control bit stream whose bytes are interleaved
with data bytes.
  0           -> literal byte
  1 0 <b>     -> b == 0: end of stream; else offset = b - 256        (-255..-1)
  1 1 <b> 4b  -> offset = (b << 4 | 4 bits) - 0x10ff                  (-4351..-256)
  after a match: gamma code g (start 1; while bit: g = 2g + bit), copy g + 1 bytes.
"""
import ctypes, os, struct

_dll = None
try:
    _dll = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lz.dll"))
    _dll.lz_decompress.restype = ctypes.c_long
    _dll.lz_decompress.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t]
    _dll.lz_compress.restype = ctypes.c_long
    _dll.lz_compress.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p]
except OSError:
    _dll = None


class BitReader:
    def __init__(self, data):
        self.d = data
        self.pos = 1
        self.cur = data[0]
        self.mask = 0x80

    def bit(self):
        if self.mask == 0:
            self.cur = self.d[self.pos]
            self.pos += 1
            self.mask = 0x80
        b = 1 if self.cur & self.mask else 0
        self.mask >>= 1
        return b

    def byte(self):
        b = self.d[self.pos]
        self.pos += 1
        return b


def decompress(data, raw_size=None):
    if _dll is not None:
        cap = raw_size if raw_size is not None else max(1 << 20, len(data) * 64)
        buf = ctypes.create_string_buffer(cap)
        n = _dll.lz_decompress(data, len(data), buf, cap)
        if n < 0:
            raise ValueError("corrupt LZ stream")
        return buf.raw[:n]
    return decompress_py(data, raw_size)


def decompress_py(data, raw_size=None):
    r = BitReader(data)
    out = bytearray()
    while True:
        if r.bit() == 0:
            out.append(r.byte())
            continue
        if r.bit() == 0:
            b = r.byte()
            if b == 0:
                break
            off = b - 256
        else:
            b = r.byte()
            n = 0
            for _ in range(4):
                n = n * 2 + r.bit()
            off = ((b << 4) | n) - 0x10FF
        g = 1
        while r.bit():
            g = g * 2 + r.bit()
        src = len(out) + off
        if src < 0:
            raise ValueError("bad back-reference")
        for i in range(g + 1):
            out.append(out[src + i])
        if raw_size is not None and len(out) > raw_size:
            raise ValueError("overrun")
    return bytes(out)


class BitWriter:
    def __init__(self):
        self.out = bytearray()
        self.flag_pos = None
        self.mask = 0

    def bit(self, b):
        if self.mask == 0:
            self.flag_pos = len(self.out)
            self.out.append(0)
            self.mask = 0x80
        if b:
            self.out[self.flag_pos] |= self.mask
        self.mask >>= 1

    def byte(self, b):
        self.out.append(b)


def _gamma_bits(g):
    # g >= 1; bits after the implicit leading 1, each preceded by a 1 "continue" bit, then a 0.
    s = bin(g)[3:]
    bits = []
    for c in s:
        bits += [1, int(c)]
    bits.append(0)
    return bits


def _cost_match(off, length):
    # bits for match token (excluding gamma) + gamma bits, in bits (bytes count as 8)
    base = (2 + 8) if off >= -255 else (2 + 8 + 4)
    return base + len(_gamma_bits(length - 1))


def compress(data):
    if _dll is not None:
        buf = ctypes.create_string_buffer(len(data) + len(data) // 8 + 64)
        n = _dll.lz_compress(data, len(data), buf)
        return buf.raw[:n]
    return compress_py(data)


def compress_py(data):
    """Optimal-parse compressor (dynamic programming over positions)."""
    n = len(data)
    MAXOFF = 0x10FF  # 4351
    INF = float("inf")
    # Hash chains for match finding.
    head = {}
    prev = [-1] * n
    cand = [None] * n
    for i in range(n):
        if i + 1 < n:
            key = data[i:i + 2]
            p = head.get(key, -1)
            prev[i] = p
            head[key] = i
    # Collect best matches per position: for each length the smallest offset (cheapest).
    for i in range(n):
        best = []  # list of (length, off)
        if i + 1 >= n:
            cand[i] = best
            continue
        p = prev[i]
        bestlen = 1
        steps = 0
        while p >= 0 and i - p <= MAXOFF and steps < 512:
            # extend
            l = 0
            maxl = n - i
            while l < maxl and data[p + l] == data[i + l]:
                l += 1
            if l > bestlen:
                for L in range(bestlen + 1, l + 1):
                    best.append((L, p - i))
                bestlen = l
                if l == maxl:
                    break
            p = prev[p]
            steps += 1
        cand[i] = best
    cost = [INF] * (n + 1)
    choice = [None] * (n + 1)
    cost[n] = 0
    for i in range(n - 1, -1, -1):
        c = 9 + cost[i + 1]
        ch = None
        for L, off in cand[i]:
            cc = _cost_match(off, L) + cost[i + L]
            if cc < c:
                c = cc
                ch = (L, off)
        cost[i] = c
        choice[i] = ch
    w = BitWriter()
    i = 0
    while i < n:
        ch = choice[i]
        if ch is None:
            w.bit(0)
            w.byte(data[i])
            i += 1
            continue
        L, off = ch
        w.bit(1)
        if off >= -255:
            w.bit(0)
            w.byte(off + 256)
        else:
            v = off + 0x10FF
            w.bit(1)
            w.byte(v >> 4)
            for k in (3, 2, 1, 0):
                w.bit((v >> k) & 1)
        for b in _gamma_bits(L - 1):
            w.bit(b)
        i += L
    # end marker
    w.bit(1)
    w.bit(0)
    w.byte(0)
    return bytes(w.out)


class Entry:
    def __init__(self, name, flags, raw_size, stored, date, extra, data):
        self.name = name
        self.flags = flags
        self.raw_size = raw_size
        self.date = date
        self.extra = extra
        self.stored = stored  # bytes as stored in archive

    def raw(self):
        if self.flags & 1:
            return decompress(self.stored, self.raw_size)[: self.raw_size]
        return self.stored[: self.raw_size]


def read_xap(blob):
    assert blob[:4] == b"XAPF", "not a XAP"
    total, hsize, bsize = struct.unpack_from("<III", blob, 4)
    assert blob[0x10:0x14] == b"FILE"
    fchunk, ver, count = struct.unpack_from("<III", blob, 0x14)
    entries = []
    for i in range(count):
        no, fl, off, raw, st, date, extra, z = struct.unpack_from("<8I", blob, 0x20 + i * 32)
        nb = blob[0x18 + no: blob.index(b"\0", 0x18 + no)]
        e = Entry(nb.decode("cp932"), fl, raw, blob[off: off + st], date, extra, None)
        e.data_offset = off
        e.stored_size = st
        e.zero = z
        entries.append(e)
    return entries


def _align(x, a):
    return (x + a - 1) // a * a


def write_xap(entries, version=1):
    """Layout: XAPF hdr (0x10) | FILE chunk at 0x10, size fsize (16-aligned end)
    | BODY chunk at 0x10+fsize: "BODY" u32(bsize-8) + 8 pad, then 16-aligned entries."""
    count = len(entries)
    names = bytearray()
    name_offs = []
    base = 8 + count * 32  # relative to 0x18
    for e in entries:
        name_offs.append(base + len(names))
        names += e.name.encode("cp932") + b"\0"
    names_end = 0x20 + count * 32 + len(names)
    body_at = _align(names_end, 16)
    fsize = body_at - 0x10
    offs = []
    pos = body_at + 0x10
    for e in entries:
        offs.append(pos)
        pos = _align(pos + len(e.stored), 16)
    total = pos
    bsize = total - body_at
    out = bytearray(total)
    out[0:4] = b"XAPF"
    struct.pack_into("<III", out, 4, total - 0x10, fsize, bsize)
    out[0x10:0x14] = b"FILE"
    struct.pack_into("<III", out, 0x14, fsize - 8, version, count)
    for i, e in enumerate(entries):
        struct.pack_into("<8I", out, 0x20 + i * 32, name_offs[i], e.flags, offs[i], e.raw_size,
                         len(e.stored), e.date, e.extra, 0)
    out[0x20 + count * 32: names_end] = names
    out[body_at:body_at + 4] = b"BODY"
    struct.pack_into("<I", out, body_at + 4, bsize - 8)
    for i, e in enumerate(entries):
        out[offs[i]: offs[i] + len(e.stored)] = e.stored
    return bytes(out)
