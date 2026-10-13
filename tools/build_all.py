"""Repack every archive with modified files under build/mod/<path>.XAP/ and build the ISO.

usage: build_all.py OUT.iso
Archive folders may be nested to mirror the disc (e.g. build/mod/MINIG/COMMON.XAP/).
Loose replacement files (non-XAP, e.g. SCPS_150.88) go in build/loose/ mirroring the disc root.
"""
import os, shutil, subprocess, sys

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(W, "tools"))
import repack

ORIG_ISO = os.path.join(os.path.dirname(W), "Bokura no Kazoku - My Family Growing Up in the 21st Century (Japan)",
                        "Bokura no Kazoku - My Family Growing Up in the 21st Century (Japan).iso")
import iso9660, tempfile


def orig_file(rel):
    """Copy DATA/<rel> out of the ORIGINAL ISO (never a mounted drive, which may be a patched
    image) into a temp file and return its path."""
    key = ("DATA/" + rel.replace(os.sep, "/")).upper()
    with open(ORIG_ISO, "rb") as f:
        for r in iso9660.walk(f)[1]:
            if r.path.upper().lstrip("/") == key:
                f.seek(r.lba * iso9660.SECTOR)
                data = f.read(r.size)
                break
        else:
            raise SystemExit(f"{key} not found in original ISO")
    t = os.path.join(tempfile.gettempdir(), "bnk_orig_" + os.path.basename(rel))
    open(t, "wb").write(data)
    return t
MOD = os.path.join(W, "build", "mod")
LOOSE = os.path.join(W, "build", "loose")
REP = os.path.join(W, "build", "rep")


def main(out_iso):
    if os.path.isdir(REP):
        shutil.rmtree(REP)
    os.makedirs(os.path.join(REP, "DATA"))
    for r, dirs, files in os.walk(MOD):
        for d in list(dirs):
            if d.upper().endswith(".XAP"):
                rel = os.path.relpath(os.path.join(r, d), MOD)
                src = orig_file(rel)
                dst = os.path.join(REP, "DATA", rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                n = repack.repack(src, os.path.join(r, d), dst, verbose=False)
                if n == 0:
                    os.remove(dst)
                else:
                    print(f"repacked {rel}: {n} files changed")
                dirs.remove(d)
    if os.path.isdir(LOOSE):
        for r, dirs, files in os.walk(LOOSE):
            for f in files:
                rel = os.path.relpath(os.path.join(r, f), LOOSE)
                dst = os.path.join(REP, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(r, f), dst)
                print(f"loose file {rel}")
    subprocess.check_call([sys.executable, "-P", os.path.join(W, "tools", "build_iso.py"), ORIG_ISO, out_iso, REP])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(W, "test.iso"))
