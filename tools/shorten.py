"""Fit pass: shorten English labels that overflow their UI slot, as whole-field substitutions
appended to tl/txt/<REL>.tsv (block regenerated on every run).

The substitutions are computed against the translated file *without* this block, so the script
can be re-run after editing SHORT. Run: shorten.py   (then txt_tl.py apply)
"""
import os, re, sys, subprocess

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = os.path.join(W, "tl", "txt")
MOD = os.path.join(W, "build", "mod")
MARK = "// --- fit pass (tools/shorten.py) ---"

ACTIONS = {
    "Christmas Date with Pooh": "Xmas Date with Pooh",
    "Go to the Used Bookstore": "Browse Used Books",
    "Go to a Japanese Restaurant": "Eat Japanese Food",
    "Go to a Hotel Restaurant": "Dine at a Hotel",
    "Shop at the Shopping Street": "Shop at the Arcade",
    "Visit the Edo-Tokyo Museum": "Edo-Tokyo Museum",
    "Cherry Blossoms at Zenpukuji": "Zenpukuji Blossoms",
    "Visit Kasai Sea Life Park": "Kasai Sea Life Park",
    "Visit the Tropical Garden": "Tropical Garden",
    "See Asagaya's Tanabata": "Asagaya Tanabata",
    "Visit Sunshine Aquarium": "Sunshine Aquarium",
    "See Art at the Western Art Museum": "Western Art Museum",
    "Visit Musashi Forest Park": "Musashi Forest Park",
}
CLUBS = {
    "Table tennis - ping pong!": "Ping pong time!",
    "Be a dolphin in swimming": "Swim like a dolphin",
    "Grow flowers in gardening": "Make flowers bloom",
    "Get hooked on manga club": "Get hooked on manga",
    "Focus the mind in archery!": "Focus in archery!",
    "Drama girl in drama club": "Be a drama girl",
    "Literature club is so zen": "Literature is so zen",
}
JOBS = {  # status-card job titles (<= ~185px @16) and list employers (<= 235px @18)
    "Livestock Station Staff": "Livestock Lab Staff",
    "Game Hardware Designer": "Hardware Designer",
    "Game Company Secretary": "Game Co. Secretary",
    "Construction Co. Employee": "Construction Staff",
    "Newspaper Reporter": "News Reporter",
    "Small Business Owner": "Business Owner",
    "Rating Agency Staff": "Ratings Analyst",
    "High School Teacher": "HS Teacher",
    "Used Bookstore Clerk": "Bookstore Clerk",
    "Vintage Clothing Clerk": "Vintage Shop Clerk",
    "Sakura Kindergarten Aide": "Kindergarten Aide",
    "Teito University Hospital": "Teito Univ. Hospital",
    "Travel Agency Bus Guide": "Bus Tour Agency",
    "Construction Company": "Construction Firm",
    "Vintage Clothing Shop": "Vintage Shop",
    "Video Game Company": "Game Company",
}
PARTS = {
    "Ramen shop dishwasher": "Ramen dishwasher",
    "Learn life by babysitting": "Babysit and learn",
    "Try convenience store work": "Work at a konbini",
    "Ring up at a used bookstore": "Bookstore cashier",
    "Convenience Store Clerk": "Konbini Clerk",
    "Used Bookstore Cashier": "Bookstore Cashier",
}
SCHOOLS = {  # system names: status cards, report card, "Goal" window (+ grade suffix)
    "Sakura Kindergarten": "Sakura Kinder",
    "Koenji Elementary": "Koenji Elem.",
    "Nobinobi Academy": "Nobinobi Elem.",
    "Suginami No.1 JHS": "Suginami JHS",
    "Clever Academy JHS": "Clever JHS",
    "Seisei Girls' JHS": "Seisei JHS",
    "Musashino Minami HS": "Musashino HS",
    "Ace Academy HS": "Ace HS",
    "Seisei Girls' HS": "Seisei HS",
    "Teito U. Medicine": "Teito U. Med.",
    "Teito U. Agriculture": "Teito U. Agri.",
    "Teito U. Engineering": "Teito U. Eng.",
    "Eurasia U. Pol/Econ": "Eurasia Econ",
    "Eurasia U. Education": "Eurasia Educ.",
    "Seisei W.U. Letters": "Seisei Lit.",
    "Seisei W.U. Business": "Seisei Bus.",
    "Seisei W.U. Intl.": "Seisei Intl.",
    "Tanaka Chiyo Fashion": "Fashion School",
    "Shinjuku Culinary JP": "Culinary (JP)",
    "Shinjuku Culinary West": "Culinary (W)",
    "Teito Nursing School": "Teito Nursing",
}
SYSMES = {
    "Kawai Juku (cram school)": "Kawai Juku (cram)",
    "Gap year without cram school": "Self-study gap year",
    "Go on to school after all": "Enroll after all",
    "No gap year after all": "Skip the gap year",
    "Take a gap year": "Gap year",
}

PLAN = {
    "GAMEDB.XAP/action.txt": ACTIONS,
    "GAMEDB.XAP/club.txt": CLUBS,
    "GAMEDB.XAP/job.txt": JOBS,
    "GAMEDB.XAP/part.txt": PARTS,
    "GAMEDB.XAP/school.txt": SCHOOLS,
    "GAMEDB.XAP/childinfo.txt": SCHOOLS,
    "RESNAME.XAP/school.txt": SCHOOLS,
    "SYSMES.XAP/sysmes.txt": SYSMES,
}


def strip_block(path):
    if not os.path.exists(path):
        return
    txt = open(path, encoding="utf-8").read()
    if MARK in txt:
        open(path, "w", encoding="utf-8").write(txt.split(MARK)[0].rstrip("\n") + "\n")


SCHOOL_ROW = re.compile(r"^(	(\d+),\s+)([^,]+)(,\s+)([^,]+)(,\s+(?:KINDER|GRAMMER|JHIGH|HIGH|COLLEGE|CRAMMER),.*)$")
# list (selection) names; the list draws its "Goal" badge at x = 57 + 10px per byte, so the
# names are padded with zero-width '@d0' codes until the badge lands just after the text
SCHOOL_LIST = {1: "Sakura Kinder", 2: "Koenji Elem.", 3: "Nobinobi Elem.", 4: "Suginami JHS",
               5: "Clever JHS", 6: "Seisei Girls' JHS", 7: "Musashino HS", 8: "Ace HS",
               9: "Seisei Girls' HS", 10: "Teito U. Medicine", 11: "Teito U. Law", 12: "Teito U. Agri.",
               13: "Teito U. Eng.", 14: "Eurasia U. Econ", 15: "Eurasia U. Educ.", 16: "Seisei Letters",
               17: "Seisei Intl.", 18: "Seisei Business", 19: "Art School", 20: "Tanaka Fashion",
               21: "Culinary (JP)", 22: "Culinary (West)", 23: "Teito Nursing", 24: "Kawai Juku"}


def school_rows(lines):
    """Full-line replacements for [SCHOOL_INFO] rows: short system name + padded list name."""
    import math
    sys.path.insert(0, os.path.dirname(__file__))
    from overflow import lines_width
    out = []
    for i, l in enumerate(lines, 1):
        m = SCHOOL_ROW.match(l)
        if not m:
            continue
        num = int(m.group(2))
        sysname = m.group(3).strip()
        sysname = SCHOOLS.get(sysname, sysname)
        if "CRAMMER" in l:
            sysname = m.group(3).strip()
        else:
            sysname += "　"   # gap before the grade; must be plain text: highlighted rows append "@e0" right after the name
        sel = SCHOOL_LIST[num]
        pad = max(0, math.ceil((lines_width(sel, 18) + 8 - len(sel.encode("cp932")) * 10) / 30))
        out.append(f"{i}	{m.group(1)}{sysname}{m.group(4)}{sel + '@d0' * pad}{m.group(6)}")
    return out


def main():
    for rel in PLAN:
        strip_block(os.path.join(TL, rel + ".tsv"))
    subprocess.run([sys.executable, "-P", os.path.join(W, "tools", "txt_tl.py"), "apply"],
                   check=True, capture_output=True)
    for rel, table in PLAN.items():
        lines = open(os.path.join(MOD, rel), "rb").read().decode("cp932").split("\r\n")
        subs = school_rows(lines) if rel == "GAMEDB.XAP/school.txt" else []
        for i, l in enumerate(lines, 1):
            if rel == "GAMEDB.XAP/school.txt" and SCHOOL_ROW.match(l):
                continue
            body = l.split("#")[0]
            for old in sorted(table, key=len, reverse=True):
                pat = r"(?:(?<=^)|(?<=[,\t =]))" + re.escape(old) + r"(?=\s*(?:,|$|\t|#|\"|@))"
                while re.search(pat, body):
                    subs.append(f"{i}\t<SUB>\t{old}\t{table[old]}")
                    body = re.sub(pat, "\x00", body, count=1)
        path = os.path.join(TL, rel + ".tsv")
        with open(path, "a", encoding="utf-8") as f:
            f.write(MARK + "\n" + "\n".join(subs) + ("\n" if subs else ""))
        print(f"{rel}: {len(subs)} substitutions")


if __name__ == "__main__":
    main()
