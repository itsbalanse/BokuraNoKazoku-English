"""Repack a XAP: replace entries whose names match files in MODDIR, keep all others verbatim.

usage: repack.py ORIGINAL.XAP MODDIR OUT.XAP
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import xap


def repack(orig_path, moddir, out_path, verbose=True):
    blob = open(orig_path, "rb").read()
    es = xap.read_xap(blob)
    mods = {f.lower(): os.path.join(moddir, f) for f in os.listdir(moddir)} if os.path.isdir(moddir) else {}
    changed = 0
    for e in es:
        p = mods.get(e.name.lower())
        if not p:
            continue
        raw = open(p, "rb").read()
        if raw == e.raw():
            continue
        if e.flags & 1:
            e.stored = xap.compress(raw)
            assert xap.decompress(e.stored) == raw
        else:
            e.stored = raw
        e.raw_size = len(raw)
        changed += 1
        if verbose:
            print(f"  {e.name}: raw {len(raw)} stored {len(e.stored)}")
    out = xap.write_xap(es)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    open(out_path, "wb").write(out)
    if verbose:
        print(f"{os.path.basename(orig_path)}: {changed} changed, {len(blob)} -> {len(out)} bytes")
    return changed


if __name__ == "__main__":
    repack(*sys.argv[1:4])
