"""Fit pass for window layouts (MENURES window.txt / menumes.txt / wheel.txt): widen windows,
move options apart and pick smaller sizes where English needs more room than the Japanese did.

Edits are emitted as <SUB>/full-line entries in a marked block at the end of each tl/txt tsv,
computed against the translated file without that block (re-runnable).
Run: layout_fit.py  (then txt_tl.py apply)
"""
import os, re, sys, subprocess

sys.path.insert(0, os.path.dirname(__file__))
from overflow import lines_width

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = os.path.join(W, "tl", "txt")
MOD = os.path.join(W, "build", "mod")
MARK = "// --- layout fit pass (tools/layout_fit.py) ---"
WIN = "MENURES.XAP/window.txt"
MES = "MENURES.XAP/menumes.txt"
WHEEL = "MENURES.XAP/wheel.txt"


class File:
    def __init__(self, rel):
        self.rel = rel
        self.lines = open(os.path.join(MOD, rel), "rb").read().decode("cp932").split("\r\n")
        self.cur = {}          # line -> edited text
        self.out = []

    def text(self, i):
        return self.cur.get(i, self.lines[i - 1])

    def section(self, name):
        start = next(i for i, l in enumerate(self.lines, 1) if l.strip() == f"[{name}]")
        end = start + 1
        while end <= len(self.lines) and not self.lines[end - 1].strip().startswith("["):
            end += 1
        return range(start + 1, end)

    def sub(self, i, old, new):
        t = self.text(i)
        assert old in t, f"{self.rel}:{i}: '{old}' not in: {t}"
        self.cur[i] = t.replace(old, new, 1)
        self.out.append(f"{i}\t<SUB>\t{old}\t{new}")

    def sub_in(self, sect, pattern, old, new, count=None):
        """SUB old->new on lines of [sect] whose text matches regex pattern."""
        n = 0
        for i in self.section(sect):
            if re.search(pattern, self.text(i)) and old in self.text(i):
                self.sub(i, old, new)
                n += 1
                if count and n >= count:
                    break
        assert n, f"{self.rel} [{sect}] no line matches {pattern} / {old}"

    def msg(self, num, new):
        """menumes: replace the text of message NNN."""
        for i, l in enumerate(self.lines, 1):
            if re.match(rf"^{num:03d}\t", l.strip()):
                self.cur[i] = f"{num:03d}\t{new}"
                self.out.append(f"{i}\t{num:03d}\t{new}")
                return
        raise SystemExit(f"menumes {num} not found")


def window(f):
    # --- action screen memo: widen to the free space left of the status panel (x 28..423)
    for kind in ("shadow", "label", "base", "line"):
        f.sub_in("sysscr31", rf"^\s*{kind},", " 263,", " 395,")
    f.sub_in("sysscr31", r"^\s*box,", " 243,", " 375,")

    # --- guide panels (school/club/job/part-time/book): 30px wider to the right
    for sect in ("infoschool", "infoclub", "infojob", "infoptjob", "infobook"):
        f.sub_in(sect, r"^\s*(shadow|base),", " 254,", " 284,")
        f.sub_in(sect, r"^\s*(box|line),", " 233,", " 263,")
        f.sub_in(sect, r'comment,\s*472,\s*32', "472", "487")
        f.sub_in(sect, r"icon,\s*365,\s*52", "365", "380")
    f.sub_in("infojob", r"string,\s*472,\s*291", "472", "487")
    f.sub_in("infobook", r"string,\s*472,\s*288", "472", "487")

    # --- status card: school/workplace line smaller (book title + icon share the row)
    f.sub_in("name", r'string,\s*198,\s*57', '"@s18@0%s"', '"@s15@0%s"')

    # --- status card header: smaller name, age moved left, birth order smaller so it fits
    f.sub_in("name", r"string,\s*207,\s*30", "@s20@0%s@r92@g87@b42@s18@0(%s)", "@s18@0%s@r92@g87@b42@s16@0(%s)")
    f.sub_in("name", r"string,\s*419,\s*30", "419,", "395,")
    f.sub_in("name", r"string,\s*451,\s*30", "451,", "427,")
    f.sub_in("name", r"string,\s*470,\s*32", '470,  32, left, "@a%d@0%s %s"', '436,  33, left, "@a%d@s14@0%s %s"')
    for sect in ("infoschool", "infoclub", "infojob", "infoptjob", "infobook"):
        f.sub_in(sect, r"string,\s*473,\s*367", '"@s15@0%s %s"', '"@s14@0%s %s"')

    # --- report card header: name and school smaller so they clear the stats table
    f.sub_in("childreport", r"string,\s*80,\s*92", "@s20@r115", "@s16@r115")
    f.sub_in("childreport", r"string,\s*80,\s*92", "@d11", "@d7")
    f.sub_in("childreport", r"string,\s*80,\s*122", "@s17@r115", "@s15@r115")

    # --- household budget
    f.sub_in("houseaccount", r"Household Budget", "Household Budget", "Budget")
    f.sub_in("houseaccount", r"string,\s*561,\s*99", "@s18@r115", "@s16@r115")
    f.sub_in("houseaccount", r"Total Salary", "Total Salary", "Salary")
    f.sub_in("houseaccount", r"Part-time Job", "Part-time Job", "Part-time")
    f.sub_in("houseaccount", r"Other Income", "Other Income", "Other")
    f.sub_in("houseaccount", r"Total Income", "Total Income", "Income")
    f.sub_in("houseaccount", r"Total Expenses", "Total Expenses", "Expenses")

    # --- settings: spread the options and use shorter labels
    f.sub_in("config", r'Back""', 'Back""', 'Back"')
    opts = [  # (old label, old center, old cursor) -> (new label, new center)
        ("Subs+Voice", 212, 148, "Voice + Text", 190),
        ("Voice Only", 319, 263, "Voice Only", 320),
        ("Subs Only", 420, 363, "Text Only", 450),
        ("Advance automatically", 211, 91, "Auto-advance", 200),
        ("Wait for a button press", 433, 300, "Wait for button", 420),
    ]
    for old, oc, ocur, new, nc in opts:
        cursor = int(nc - lines_width(new, 18) / 2 - 19)
        for i in f.section("config"):
            t = f.text(i)
            m = re.search(rf'string,\s*{oc},(\s*\d+,\s*center,\s*"%s@0){re.escape(old)}",\s*{ocur},', t)
            if m:
                f.sub(i, m.group(0), f'string, {nc},{m.group(1)}{new}", {cursor},')
                break
        else:
            raise SystemExit(f"config option {old} not found")

    # --- name lists (4 columns of 110px at size 22): smaller names so long ones stay inside
    for sect in ("sysscr09", "sysscr23"):
        for i in f.section(sect):
            if re.match(r'^\s*string,\s*\d+,\s*\d+,\s*left,\s*"%s",', f.text(i)):
                f.sub(i, '"%s"', '"@s19%s"')
    f.sub_in("sysscr22", r"Please name the baby", "@s19Please name the baby", "@s19Name the baby")

    # --- save/load album picker title, family album intro
    f.sub_in("sysscr16_1", r"Choose a Family Album", "Choose a Family Album", "Pick an Album")
    f.sub_in("memorial", r"comment,\s*230,\s*186", "230, 186, left, \"@s18Our family's growth\"",
             "320, 186, center, \"@s18Our family's story,\"")
    f.sub_in("memorial", r"comment,\s*266,\s*208", "266, 208, left, \"@s18and memories in photos.\"",
             "320, 208, center, \"@s18told in photos.\"")

    # --- salary review: labels left of the coins, score label clear of the number
    f.sub_in("reviewselect2", r"comment,\s*420,\s*143", "420, 143", "404, 143")
    f.sub_in("reviewselect2", r"comment,\s*420,\s*170", "420, 170", "404, 170")
    f.sub_in("reviewselect2", r"comment,\s*411,\s*196", "411, 196", "404, 196")
    f.sub_in("reviewresult1", r"Clear Rate", "@s18Clear Rate", "@s18Score")
    for kind in ("shadow", "base"):
        f.sub_in("reviewresult2", rf"^\s*{kind},", " 230,", " 248,")
    for old, new in (("icon, 285, 246", "icon, 297, 246"), ("icon, 318, 250", "icon, 330, 250"),
                     ("comment, 338, 252", "comment, 350, 252"), ("icon, 356, 250", "icon, 368, 250"),
                     ("comment, 377, 252", "comment, 389, 252"), ("icon, 396, 248", "icon, 408, 248")):
        f.sub_in("reviewresult2", re.escape(old).replace(r"\ ", r"\s*"), old, new)

    # --- yearly income / deposit popups
    f.sub_in("getmoney1", r"This Year's Income", "comment, 268, 130", "comment, 240, 130")
    f.sub_in("exgetmoney", r'"Total Savings"', '"Total Savings"', '"Savings"')
    f.sub_in("getmoney2", r"Total Savings", "@s16Total Savings", "@s16Savings")

    # --- subject gauges (Lit/Sci/Art/Spt): move the bar 4px right, widen the label column
    f.sub_in("intgauge", r"icon,\s*29,\s*3", "29", "33")
    f.sub_in("status", r"box,\s*420,\s*234,\s*20,", " 20,", " 26,")
    f.sub_in("status", r"box,\s*440,\s*234,\s*135,", "440, 234, 135,", "446, 234, 129,")


def menumes(f):
    lab = "@r115@g115@b86"
    for num, s in ((39, "Pers"), (40, "Mind"), (41, "Love"), (42, "Drive"), (43, "Body")):
        f.msg(num, f"@d1@s14{lab}{s}")
    for num, s in ((44, "Lit"), (45, "Sci"), (46, "Art"), (47, "Spt")):
        f.msg(num, f"@s14{lab}{s}")
    ok = "@s18@r74@g42@b40○@s4　@s20@r115@g115@b115"
    f.msg(49, ok + "Report Card")
    f.msg(53, ok + "OK　@s18←→@s20 Other kids")
    f.msg(59, "@s19←→ Photo　　@r10@g71@b40△@r115@g115@b115 Slideshow")
    for num, s in ((116, "Merit Pay"), (117, "Seniority"), (118, "Child Aid"), (119, "Total Pay")):
        f.msg(num, "@s16" + s)
    # grade suffix after the school name: "<school> 2 yr", "<school> K2"
    f.msg(162, "@d3yr")
    f.msg(172, "@d4yrs in,@d5")
    # character-type speech bubbles hold ~77px per line: split long words like "Day-/dreamer"
    f.msg(212, "@s15@s5　@n@s16Book-@nworm")
    f.msg(214, "@s15@s5　@n@s16Delin-@nquent")
    for num, s in ((163, "K1"), (164, "K2"), (165, "K3")):
        f.msg(num, s)


def wheel(f):
    # keep every label inside the panel (x 414..572) at the wheel's 16px font
    for i, l in enumerate(f.lines, 1):
        m = re.match(r'^(\s*)(\d+),\s*(\d+),\s*"([^"]+)"', l)
        if not m:
            continue
        x = int(m.group(2))
        w = lines_width(m.group(4), 16)
        nx = min(max(x, 414), int(572 - w))
        if nx != x:
            f.sub(i, f"{m.group(2)}, {m.group(3)}", f"{nx}, {m.group(3)}")


def strip(rel):
    path = os.path.join(TL, rel + ".tsv")
    txt = open(path, encoding="utf-8").read()
    if MARK in txt:
        open(path, "w", encoding="utf-8").write(txt.split(MARK)[0].rstrip("\n") + "\n")


def main():
    for rel in (WIN, MES, WHEEL):
        strip(rel)
    subprocess.run([sys.executable, "-P", os.path.join(W, "tools", "txt_tl.py"), "apply"],
                   check=True, capture_output=True)
    for rel, fn in ((WIN, window), (MES, menumes), (WHEEL, wheel)):
        f = File(rel)
        fn(f)
        with open(os.path.join(TL, rel + ".tsv"), "a", encoding="utf-8") as out:
            out.write(MARK + "\n" + "\n".join(f.out) + "\n")
        print(f"{rel}: {len(f.out)} edits")


if __name__ == "__main__" and "--news" not in sys.argv:
    main()


# ---------------------------------------------------------------------------
# Family News (GAMEMES.XAP/gamemes.mes): rewrap messages into the 376px news box, 1-3 lines.
NEWS = "GAMEMES.XAP/gamemes.mes"


def news():
    from textfit import wrap
    strip(NEWS)
    subprocess.run([sys.executable, "-P", os.path.join(W, "tools", "txt_tl.py"), "apply"],
                   check=True, capture_output=True)
    lines = open(os.path.join(MOD, NEWS), "rb").read().decode("cp932").split("\r\n")
    out, bad = [], []
    for i, l in enumerate(lines, 1):
        m = re.match(r"^(\s*)@d0(.*)$", l)
        if not m:
            continue
        body = m.group(2)
        tail = "@n" if body.endswith("@n") else ""
        core = body[:-2] if tail else body
        parts = core.split("@n")
        if max(lines_width(p, 20) for p in parts) <= 352:
            continue
        new = wrap(" ".join(p.strip() for p in parts), max_px=352, size=20)
        if len(new) > 3:
            bad.append((i, core))
        out.append(f"{i}\t{m.group(1)}@d0" + "@n".join(new) + (tail if len(new) < 3 else ""))
    with open(os.path.join(TL, NEWS + ".tsv"), "a", encoding="utf-8") as f:
        f.write(MARK + "\n" + "\n".join(out) + "\n")
    print(f"{NEWS}: {len(out)} rewrapped; >3 lines: {bad}")


if __name__ == "__main__" and "--news" in sys.argv:
    news()
