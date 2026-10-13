"""Background PCSX2 actions: act.py KEY[:ms][*n] wait:ms shot:name ...  (keys posted to the game window)"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from bgpad import key, wait, shot
for c in sys.argv[1:]:
    name, _, arg = c.partition(":")
    if name == "wait":
        wait(int(arg))
    elif name == "untilmenu":
        # press Circle until the action menu header (from shots/p40.png) is on screen
        from PIL import Image, ImageChops, ImageStat
        ref = Image.open(os.path.join(os.path.dirname(__file__), "..", "shots", "p40.png")).convert("RGB").crop((28, 36, 120, 60))
        for i in range(int(arg or 60)):
            p = shot("cur")
            im = Image.open(p).convert("RGB").crop((28, 36, 120, 60))
            if sum(ImageStat.Stat(ImageChops.difference(im, ref)).mean) / 3 < 14:
                print("action menu after", i); break
            key("C"); wait(1000)
    elif name == "shot":
        print(shot(arg) or f"shot {arg} FAILED")
    else:
        ms, n = 120, 1
        if "*" in arg:
            a, b = arg.split("*"); ms, n = int(a or 120), int(b)
        elif arg:
            ms = int(arg)
        for _ in range(n):
            key(name, ms); wait(250)
