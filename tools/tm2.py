"""PS2 TIM2 (.tm2) decode/encode for single- or multi-picture files.

Supported image types: 1=16bit, 2=24bit, 3=32bit, 4=4bit indexed, 5=8bit indexed.
CLUT types: 16/24/32-bit colours; CSM1 swizzle for 256-colour CLUTs (bit 7 of clut type clear).
PS2 alpha 0x80 = opaque; mapped to 255 on export and back on import.
"""
import struct, sys, os
from PIL import Image


def _a_in(a):
    return min(255, a * 2) if a < 0x80 else 255


def _a_out(a):
    return (a + 1) // 2 if a < 255 else 0x80


def _swizzle_index(i):
    # CSM1: within each 32-entry block, entries 8-15 and 16-23 are swapped
    blk = i & ~31
    r = i & 31
    if 8 <= r < 16:
        r += 8
    elif 16 <= r < 24:
        r -= 8
    return blk | r


def _read_color(b, o, bpp):
    if bpp == 2:
        v = struct.unpack_from("<H", b, o)[0]
        return ((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3, 255 if v & 0x8000 else 0)
    if bpp == 3:
        return (b[o], b[o + 1], b[o + 2], 255)
    return (b[o], b[o + 1], b[o + 2], _a_in(b[o + 3]))


def _write_color(c, bpp):
    r, g, bb, a = c
    if bpp == 2:
        return struct.pack("<H", (r >> 3) | ((g >> 3) << 5) | ((bb >> 3) << 10) | (0x8000 if a >= 128 else 0))
    if bpp == 3:
        return bytes((r, g, bb))
    return bytes((r, g, bb, _a_out(a)))


class Picture:
    pass


def parse(data):
    assert data[:4] == b"TIM2", "not TIM2"
    ver, fmt, count = struct.unpack_from("<BBH", data, 4)
    pos = 16 if fmt == 0 else 128
    pics = []
    for _ in range(count):
        p = Picture()
        (p.total, p.clut_size, p.image_size, p.header_size, p.clut_colors, p.pict_format, p.mipmaps,
         p.clut_type, p.image_type, p.width, p.height) = struct.unpack_from("<IIIHHBBBBHH", data, pos)
        p.header = data[pos: pos + p.header_size]
        p.offset = pos
        img_off = pos + p.header_size
        p.image = data[img_off: img_off + p.image_size]
        p.clut = data[img_off + p.image_size: img_off + p.image_size + p.clut_size]
        pics.append(p)
        pos += p.total
    return data[:pos if fmt == 0 else 128][:16 if fmt == 0 else 128], pics


def clut_colors(p):
    bpp = {1: 2, 2: 3, 3: 4}[p.clut_type & 0x1F]
    n = p.clut_colors
    cols = [_read_color(p.clut, i * bpp, bpp) for i in range(n)]
    if n == 256 and not (p.clut_type & 0x80):
        cols = [cols[_swizzle_index(i)] for i in range(n)]
    return cols, bpp


def to_image(p):
    w, h = p.width, p.height
    if p.image_type in (4, 5):
        cols, _ = clut_colors(p)
        if p.image_type == 5:
            idx = list(p.image[: w * h])
        else:
            idx = []
            for byte in p.image[: (w * h + 1) // 2]:
                idx += [byte & 15, byte >> 4]
            idx = idx[: w * h]
        im = Image.new("RGBA", (w, h))
        im.putdata([cols[i] if i < len(cols) else (0, 0, 0, 0) for i in idx])
        return im
    bpp = {1: 2, 2: 3, 3: 4}[p.image_type]
    im = Image.new("RGBA", (w, h))
    im.putdata([_read_color(p.image, i * bpp, bpp) for i in range(w * h)])
    return im


def from_image(p, im):
    """Re-encode an edited RGBA image into picture p (same size/format). Indexed formats are
    quantized to the existing CLUT (palette kept unchanged)."""
    im = im.convert("RGBA")
    assert im.size == (p.width, p.height), "size mismatch"
    px = list(im.getdata())
    if p.image_type in (4, 5):
        cols, _ = clut_colors(p)
        cache = {}

        def nearest(c):
            if c in cache:
                return cache[c]
            best, bd = 0, 1 << 60
            wa = c[3] / 255  # colour matters less the more transparent the pixel is
            for i, k in enumerate(cols):
                d = wa * ((c[0] - k[0]) ** 2 + (c[1] - k[1]) ** 2 + (c[2] - k[2]) ** 2) + 3 * (c[3] - k[3]) ** 2
                if d < bd:
                    best, bd = i, d
            cache[c] = best
            return best
        idx = [nearest(c) for c in px]
        if p.image_type == 5:
            p.image = bytes(idx) + p.image[len(idx):]
        else:
            out = bytearray()
            for i in range(0, len(idx), 2):
                out.append((idx[i] & 15) | ((idx[i + 1] & 15) << 4 if i + 1 < len(idx) else 0))
            p.image = bytes(out) + p.image[len(out):]
    else:
        bpp = {1: 2, 2: 3, 3: 4}[p.image_type]
        p.image = b"".join(_write_color(c, bpp) for c in px) + p.image[len(px) * bpp:]


def rebuild(data, pics):
    out = bytearray(data)
    for p in pics:
        img_off = p.offset + p.header_size
        out[img_off: img_off + p.image_size] = p.image[: p.image_size]
    return bytes(out)


if __name__ == "__main__":
    # tm2.py export DIR OUTDIR   -> PNG for every .tm2 (first picture)
    cmd = sys.argv[1]
    if cmd == "export":
        src, dst = sys.argv[2], sys.argv[3]
        os.makedirs(dst, exist_ok=True)
        n = 0
        for f in sorted(os.listdir(src)):
            if not f.lower().endswith(".tm2"):
                continue
            try:
                hdr, pics = parse(open(os.path.join(src, f), "rb").read())
                for k, p in enumerate(pics):
                    to_image(p).save(os.path.join(dst, f[:-4] + (f"_{k}" if k else "") + ".png"))
                n += 1
            except Exception as e:
                print("fail", f, e)
        print("exported", n)
