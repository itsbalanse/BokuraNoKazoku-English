"""Repaint Japanese text in UI textures with English and write them to build/mod/.

Each job: (xap_dir, tm2_name, [ops]); ops are
  ("clear", (x, y, w, h))                      -> fully transparent
  ("fill",  (x, y, w, h), (r, g, b, a))        -> solid colour
  ("text",  (x, y, w, h), text, style)          -> text auto-fitted & centred in the box
style keys: font, max (max px size), top/bot (gradient colours), outline (colour or None),
            ow (outline width), shadow ((dx, dy, (r,g,b,a)) or None), italic-ish via font choice.
Result is quantized to the texture's original palette (CLUT left unchanged).
"""
import os, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

sys.path.insert(0, os.path.dirname(__file__))
import tm2

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(W, "extracted", "DATA")
OUT = os.path.join(W, "build", "mod")
PREVIEW = os.path.join(W, "tex", "_en")
FONTS = "C:/Windows/Fonts/"
SS = 4  # supersampling


def text_mask(text, font_file, size, track=0):
    """AA alpha mask (1x) of text at `size` px, cropped to ink."""
    f = ImageFont.truetype(FONTS + font_file, size * SS)
    # draw char by char to allow tracking (letter-spacing) adjustments
    widths = [f.getlength(c) for c in text]
    tw = int(sum(widths) + track * SS * (len(text) - 1)) + 8 * SS
    th = size * SS * 2
    m = Image.new("L", (tw, th), 0)
    d = ImageDraw.Draw(m)
    x = 4 * SS
    for c, w in zip(text, widths):
        d.text((x, size * SS // 2), c, font=f, fill=255)
        x += w + track * SS
    bb = m.getbbox()
    m = m.crop(bb)
    return m.resize((max(1, round(m.width / SS)), max(1, round(m.height / SS))), Image.LANCZOS)


def render(box, text, st):
    x, y, w, h = box
    ow = st.get("ow", 1) if st.get("outline") else 0
    sh = st.get("shadow")
    pad_x = 2 * ow + (abs(sh[0]) if sh else 0)
    pad_y = 2 * ow + (abs(sh[1]) if sh else 0)
    track = st.get("track", 0)
    size = st.get("max", h)
    while True:
        m = text_mask(text, st["font"], size, track)
        if (m.width + pad_x <= w and m.height + pad_y <= h) or size <= 6:
            break
        size -= 1
    if st.get("stretch") and m.width + pad_x > w:
        m = m.resize((w - pad_x, m.height), Image.LANCZOS)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ox = (w - m.width - (sh[0] if sh else 0)) // 2
    oy = (h - m.height - (sh[1] if sh else 0)) // 2 + st.get("dy", 0)
    full = Image.new("L", (w, h), 0)
    full.paste(m, (ox, oy))
    out_m = full
    if ow:
        out_m = full.filter(ImageFilter.MaxFilter(2 * ow + 1))
    if sh:
        dx, dy, col = sh
        s = ImageChops.offset(out_m, dx, dy).point(lambda v: v * col[3] // 255)
        layer.paste(Image.new("RGBA", (w, h), col[:3] + (255,)), (0, 0), s)
    if ow:
        lay2 = Image.new("RGBA", (w, h), tuple(st["outline"][:3]) + (255,))
        layer.alpha_composite(Image.composite(lay2, Image.new("RGBA", (w, h), (0, 0, 0, 0)), out_m))
    top, bot = st["top"], st.get("bot", st["top"])
    grad = Image.new("RGBA", (w, h))
    for yy in range(h):
        t = 0 if m.height <= 1 else min(1, max(0, (yy - oy) / (m.height - 1)))
        grad.paste(tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,), (0, yy, w, yy + 1))
    layer.alpha_composite(Image.composite(grad, Image.new("RGBA", (w, h), (0, 0, 0, 0)), full))
    return layer, size


GRAY = dict(font="ARIALNB.TTF", max=13, top=(200, 200, 200), bot=(150, 150, 150), outline=(24, 24, 24), ow=1)
SEASON = lambda c: dict(font="ARIALNB.TTF", max=14, top=tuple(min(255, v + 40) for v in c),
                        bot=tuple(max(0, v - 25) for v in c), outline=(36, 36, 36), ow=1,
                        shadow=(1, 1, (20, 20, 20, 140)))
DECO = lambda c: dict(font="comicbd.ttf", max=30, top=tuple(min(255, v + 50) for v in c),
                      bot=tuple(max(0, v - 30) for v in c), outline=(10, 10, 10), ow=2,
                      shadow=(1, 1, (0, 0, 0, 160)))
GOLD = dict(font="GOTHICB.TTF", max=26, top=(222, 200, 128), bot=(140, 112, 60), outline=(30, 26, 20), ow=1,
            shadow=(1, 1, (0, 0, 0, 170)))

JOBS = [
    ("MENURES.XAP", "sysicn01", [
        ("clear", (1, 0, 30, 16)), ("text", (1, 0, 30, 16), "Shy", GRAY),
        ("clear", (31, 0, 30, 15)), ("text", (31, 0, 28, 15), "Social", dict(GRAY, track=-0.6)),
        ("clear", (62, 0, 42, 15)), ("text", (62, 0, 42, 15), "Pure", GRAY),
        ("clear", (103, 0, 44, 15)), ("text", (103, 0, 44, 15), "Mature", GRAY),
        ("clear", (147, 0, 48, 15)), ("text", (147, 0, 48, 15), "Breezy", GRAY),
        ("clear", (196, 0, 47, 15)), ("text", (196, 0, 47, 15), "Gentle", GRAY),
        ("clear", (2, 34, 26, 24)), ("text", (2, 34, 26, 24), "Spr", SEASON((190, 110, 110))),
        ("clear", (29, 34, 26, 24)), ("text", (29, 34, 26, 24), "Sum", SEASON((75, 150, 111))),
        ("clear", (57, 34, 28, 24)), ("text", (57, 34, 28, 24), "Fall", SEASON((190, 125, 80))),
        ("clear", (85, 34, 27, 24)), ("text", (85, 34, 27, 24), "Win", SEASON((118, 117, 170))),
    ]),
    ("MENURES.XAP", "sysicn06", [
        ("clear", (160, 0, 78, 41)), ("text", (160, 2, 78, 37), "Budget", DECO((100, 135, 135))),
        ("clear", (160, 42, 78, 41)), ("copy", (160, 142, 51, 34), (159, 53, 36, 24)),
        ("text", (190, 44, 48, 34), "Diary", DECO((86, 140, 80))),
        ("clear", (160, 83, 46, 23)), ("text", (160, 83, 46, 23), "All", dict(DECO((170, 95, 70)), ow=1)),
        ("clear", (172, 119, 50, 22)), ("text", (172, 119, 50, 22), "Picks", dict(DECO((170, 85, 55)), ow=1)),
    ]),
    ("MENURES.XAP", "sysicn08", [
        ("clear", (0, 0, 80, 32)), ("text", (0, 0, 80, 32), "Grades", GOLD),
    ]),
    ("MENURES.XAP", "sysicn10", [
        ("clear", (0, 0, 56, 24)), ("text", (0, 0, 54, 20), "Goal", dict(GOLD, max=19)),
    ]),
    ("MENURES.XAP", "sysicn11", [
        ("clear", (23, 0, 81, 32)), ("text", (25, 2, 79, 28), "Ending", dict(GOLD, font="comicbd.ttf", ow=2)),
    ]),
    ("INTERF.XAP", "a_onsei", [
        ("fill", (7, 3, 36, 15), (7, 7, 7, 255)),
        ("text", (7, 3, 36, 15), "VOICE", dict(font="ARIALNB.TTF", max=12, top=(180, 184, 188), bot=(130, 134, 138))),
    ]),
]


def main(only=None):
    os.makedirs(PREVIEW, exist_ok=True)
    for xap, name, ops in JOBS:
        if only and name not in only:
            continue
        path = os.path.join(SRC, xap, name + ".tm2")
        data = open(path, "rb").read()
        hdr, pics = tm2.parse(data)
        p = pics[0]
        im = tm2.to_image(p)
        for op in ops:
            if op[0] == "clear":
                x, y, w, h = op[1]
                im.paste((0, 0, 0, 0), (x, y, x + w, y + h))
            elif op[0] == "copy":
                # copy a sprite from the original texture, scaled into a new rect
                sx, sy, sw, sh = op[1]
                dx, dy, dw, dh = op[2]
                spr = tm2.to_image(p).crop((sx, sy, sx + sw, sy + sh)).resize((dw, dh), Image.LANCZOS)
                im.alpha_composite(spr, (dx, dy))
            elif op[0] == "fill":
                x, y, w, h = op[1]
                im.paste(op[2], (x, y, x + w, y + h))
            else:
                layer, size = render(op[1], op[2], op[3])
                im.alpha_composite(layer, op[1][:2])
                print(f"{name}: '{op[2]}' size {size}")
        tm2.from_image(p, im)
        new = tm2.rebuild(data, pics)
        dst = os.path.join(OUT, xap, name + ".tm2")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(new)
        # preview of what the game will actually see (after palette quantization)
        tm2.to_image(tm2.parse(new)[1][0]).save(os.path.join(PREVIEW, name + ".png"))


# ---------------------------------------------------------------------------
# Child portrait captions (MENU.XAP <kid><stage>_<08|10>.tm2): "<name>  <age>歳〜 / <type>"
# drawn in white with a black outline at the bottom-left. Erase by diffusion inpainting
# and redraw in English.
KID_NAMES = {"mok": "Mock", "jij": "Jiji", "kyo": "Kyoro", "kok": "Kokko"}
AGES = ["Age 0", "Age 1+", "Age 7+", "Age 13+", "Age 16+", "Age 19+", "Adult, Single"]
CAP_STYLE = dict(font="tahomabd.ttf", top=(255, 255, 255), outline=(0, 0, 0), ow=1)


def caption_type(stage, var):
    if var == "08":
        return "Clingy Baby" if stage < 3 else "Still a Kid"
    return "Rowdy" if stage < 3 else "Delinquent"


def caption_mask(im):
    """Mask of the caption (white glyphs + black outline) in the bottom-left corner."""
    w, h = im.size
    x0, y0, x1, y1 = 0, h - 48, min(w, 140), h - 2
    m = Image.new("L", im.size, 0)
    px = im.load()
    mp = m.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b, a = px[x, y]
            if (r > 215 and g > 215 and b > 215) or (r < 45 and g < 45 and b < 45):
                mp[x, y] = 255
    # keep only the dense caption band: drop isolated pixels then grow by 1
    m = m.filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.MaxFilter(5))
    return m


def inpaint(im, mask, iters=60):
    """Fill masked pixels by repeated neighbour averaging from the unmasked border inward."""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    mk = mask.load()
    known = [[mk[x, y] == 0 for x in range(w)] for y in range(h)]
    todo = [(x, y) for y in range(h) for x in range(w) if not known[y][x]]
    for _ in range(iters):
        if not todo:
            break
        nxt, upd = [], []
        for x, y in todo:
            acc = [0, 0, 0]; n = 0
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h and known[yy][xx]:
                    c = px[xx, yy]; acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]; n += 1
            if n >= 2:
                upd.append((x, y, (acc[0] // n, acc[1] // n, acc[2] // n, 255)))
            else:
                nxt.append((x, y))
        for x, y, c in upd:
            px[x, y] = c; known[y][x] = True
        todo = nxt
    return im


def portraits(names=None):
    src = os.path.join(SRC, "MENU.XAP")
    for f in sorted(os.listdir(src)):
        mm = re.match(r"(mok|jij|kyo|kok)(\d)_(08|10)\.tm2$", f)
        if not mm:
            continue
        kid, stage, var = mm.group(1), int(mm.group(2)), mm.group(3)
        if kid != "mok" and var != "10":
            continue
        if names and f[:-4] not in names:
            continue
        data = open(os.path.join(src, f), "rb").read()
        hdr, pics = tm2.parse(data)
        p = pics[0]
        im = tm2.to_image(p)
        mask = caption_mask(im)
        bb = mask.getbbox()
        im = inpaint(im, mask)
        # soften the filled area a little so it reads as background
        blur = im.filter(ImageFilter.GaussianBlur(1.5))
        im = Image.composite(blur, im, mask.filter(ImageFilter.MaxFilter(3)))
        h = im.height
        l1 = f"{KID_NAMES[kid]}  {AGES[stage]}"
        l2 = caption_type(stage, var)
        for text, y in ((l1, h - 41), (l2, h - 24)):
            layer, size = render((2, y, 120, 17), text, dict(CAP_STYLE, max=12))
            # left-align: shift the centred render to the left edge
            bbox = layer.getbbox()
            layer = layer.crop(bbox)
            im.alpha_composite(layer, (3, y + bbox[1]))
        tm2.from_image(p, im)
        new = tm2.rebuild(data, pics)
        dst = os.path.join(OUT, "MENU.XAP", f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(new)
        tm2.to_image(tm2.parse(new)[1][0]).save(os.path.join(PREVIEW, f[:-4] + ".png"))
        print(f, "caption bbox", bb)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["portraits"]:
        portraits(args[1:] or None)
    elif args[:1] == ["all"]:
        main(); portraits()
    else:
        main(args or None)
