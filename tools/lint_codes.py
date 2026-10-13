"""Flag control codes whose numeric argument swallowed following text digits
(e.g. '@s16' + '0%' -> '@s160'). Checks every file under build/mod."""
import os, re, sys

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMITS = {"s": 40, "d": 99, "r": 255, "g": 255, "b": 255, "o": 9, "h": 9, "e": 9, "w": 9, "n": -1, "d": 99, "a": 255}
bad = 0
for r, d, fs in os.walk(os.path.join(W, "build", "mod")):
    for f in fs:
        if not f.endswith((".txt", ".mes")):
            continue
        t = open(os.path.join(r, f), "rb").read().decode("cp932", "replace")
        for i, line in enumerate(t.split("\r\n"), 1):
            for m in re.finditer(r"@([a-z])([0-9]+)", line):
                lim = LIMITS.get(m.group(1))
                if lim is not None and int(m.group(2)) > lim:
                    bad += 1
                    print(f"{os.path.relpath(os.path.join(r, f), W)}:{i}: {m.group()} in: {line.strip()[:100]}")
print("suspicious codes:", bad)
