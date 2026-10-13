"""Build a patched ISO: copy the original, then replace files (in place when they fit in the
original sector allocation, otherwise relocated into free space after the last file).

usage: build_iso.py ORIGINAL.iso OUT.iso REPLACEMENT_DIR
  REPLACEMENT_DIR mirrors the disc layout, e.g. REPLACEMENT_DIR/DATA/EVENT.XAP, REPLACEMENT_DIR/SCPS_150.88
"""
import os, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
import iso9660 as iso

SECTOR = iso.SECTOR


def sectors(n):
    return (n + SECTOR - 1) // SECTOR


def main(orig, out, repdir):
    reps = {}
    for r, d, fs in os.walk(repdir):
        for f in fs:
            full = os.path.join(r, f)
            rel = os.path.relpath(full, repdir).replace(os.sep, "/").upper()
            reps[rel] = full
    print(f"copying {orig} -> {out}")
    shutil.copyfile(orig, out)
    with open(out, "r+b") as f:
        vol, recs = iso.walk(f)
        by_path = {r.path.upper(): r for r in recs}
        file_end = max(r.lba + sectors(r.size) for r in recs if not r.is_dir)
        next_free = file_end
        for rel, src in sorted(reps.items()):
            if rel not in by_path:
                raise SystemExit(f"not on disc: {rel}")
            rec = by_path[rel]
            data = open(src, "rb").read()
            old_alloc = sectors(rec.size)
            force = rel in os.environ.get("FORCE_RELOCATE", "").upper().split(",")
            if sectors(len(data)) <= old_alloc and not force:
                lba = rec.lba
                where = "in place"
                pad = old_alloc * SECTOR - len(data)
            else:
                lba = next_free
                next_free += sectors(len(data))
                where = f"relocated (was lba {rec.lba}, {old_alloc} sectors)"
                pad = sectors(len(data)) * SECTOR - len(data)
            f.seek(lba * SECTOR)
            f.write(data + b"\0" * pad)
            iso.set_record(f, rec, lba, len(data))
            print(f"  {rel:28} {len(data):10d} bytes @ lba {lba} {where}")
        if next_free > vol:
            iso.set_volume_space(f, next_free)
            f.truncate(next_free * SECTOR)
            print(f"volume grown to {next_free} sectors")
        print(f"free tail sectors used: {next_free - file_end}, still free: {max(0, vol - next_free)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
