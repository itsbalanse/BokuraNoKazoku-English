"""Parse font20.moj glyph metrics. Entry (12 bytes): u16 code, u8 xoff, u8 yoff, u32 bitmap offset,
u8 width, u8 height, u16 pad. Codes are ASCII (<0x100) or Shift-JIS (>=0x8140)."""
import struct, sys


def load(path):
    b = open(path, "rb").read()
    assert b[:4] == b"MOJI"
    count = struct.unpack_from("<I", b, 0x60)[0]
    g = {}
    for i in range(count):
        code, xo, yo, off, w, h, pad = struct.unpack_from("<HBBIBBH", b, 0x64 + i * 12)
        g[code] = (xo, yo, w, h)
    return g


if __name__ == "__main__":
    g = load(sys.argv[1])
    print(len(g), "glyphs")
    for c in range(0x20, 0x7F):
        if c in g:
            print(repr(chr(c)), g[c])
