"""Background auto-player: press Circle repeatedly and react to recognised screens.
drive.py STEPS [--exam] [--keep]   (PCSX2 must already be running via bg.ps1 / bg_test.ps1)
  --exam  at the school-choice screen pick the second school (Nobinobi -> entrance exam)
  --keep  keep every frame as shots/dNNN.png
"""
import sys, os
from PIL import Image, ImageChops, ImageStat
sys.path.insert(0, os.path.dirname(__file__))
from bgpad import key, wait, shot, SHOTS

ref = Image.open(os.path.join(SHOTS, "e2.png")).convert("RGB").crop((40, 50, 330, 80))


def diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


prev, same = None, 0
hist = []  # recent thumbnails, to detect A-B-A-B loops (e.g. diary <-> report card)
for step in range(int(sys.argv[1])):
    key("C")
    wait(500 if "--fast" in sys.argv else 1200)
    path = shot("cur")
    if not path:
        print(step, "no screenshot"); continue
    im = Image.open(path).convert("RGB")
    if "--keep" in sys.argv:
        im.save(os.path.join(SHOTS, "run", f"d{step:03d}.png"))
    if "--exam" in sys.argv and diff(im.crop((40, 50, 330, 80)), ref) < 12:
        print(step, "school screen -> second option", flush=True)
        key("Down"); wait(400); shot("school"); key("C"); wait(2000)
    if "--until35" in sys.argv:
        from yeardet import score
        if score(im) > 0.9:
            print(step, "YEAR 35 reached", flush=True)
            break
    small = im.resize((64, 48))
    hist = (hist + [small])[-6:]
    if len(hist) == 6 and all(diff(hist[k], hist[k + 2]) < 3 for k in range(4)) and diff(hist[-1], hist[-2]) > 6:
        print(step, "loop -> Back", flush=True)
        key("X"); wait(1200); key("X"); wait(1200)
        key("Down"); wait(300); key("Down"); wait(300); hist = []
    if prev is not None and diff(small, prev) < 2:
        same += 1
        if same >= 3:
            print(step, "stuck -> Down", flush=True)
            key("Down"); wait(300); same = 0
    else:
        same = 0
    prev = small
