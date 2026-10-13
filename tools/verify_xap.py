import sys, os, glob, struct, time
sys.path.insert(0, os.path.dirname(__file__))
import xap

ISO_ROOT = sys.argv[1] if len(sys.argv) > 1 else "H:/"
EXTRACTED = sys.argv[2] if len(sys.argv) > 2 else "extracted"
SKIP_BIG = 40_000_000
ok = bad = noref = 0
rt_ok = rt_bad = 0
orig_c = new_c = 0
for p in sorted(glob.glob(os.path.join(ISO_ROOT, "DATA", "**", "*.XAP"), recursive=True)):
    if os.path.getsize(p) > 200_000_000:
        continue
    b = open(p, "rb").read()
    es = xap.read_xap(b)
    rebuilt = xap.write_xap(es)
    same = rebuilt == b
    if not same:
        diff = next((i for i in range(min(len(b), len(rebuilt))) if b[i] != rebuilt[i]), None)
        print(f"{os.path.basename(p)}: rebuild differs len {len(b)} vs {len(rebuilt)} first diff {diff}")
    rel = os.path.relpath(p, ISO_ROOT)
    for e in es:
        ref = os.path.join(EXTRACTED, rel, e.name)
        if len(b) > SKIP_BIG and not os.path.exists(ref):
            continue
        try:
            r = e.raw()
        except Exception as ex:
            bad += 1
            print("  FAIL", rel, e.name, ex)
            continue
        if os.path.exists(ref):
            if open(ref, "rb").read() == r:
                ok += 1
            else:
                bad += 1
                print("  MISMATCH", rel, e.name)
        else:
            noref += 1
        # compressor round-trip on text files only (speed)
        if e.flags & 1 and e.name.endswith((".txt", ".mes")):
            c = xap.compress(r)
            if xap.decompress(c) == r:
                rt_ok += 1
            else:
                rt_bad += 1
                print("  ROUNDTRIP FAIL", rel, e.name)
            orig_c += e.stored_size
            new_c += len(c)
print("decode ok", ok, "bad", bad, "unreferenced(decoded fine)", noref)
print("compress roundtrip ok", rt_ok, "bad", rt_bad, "orig stored", orig_c, "mine", new_c)
