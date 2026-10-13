"""Minimal ISO9660 reader + in-place/relocating file replacer for PS2 DVD images.

Directory records are patched in place (LBA + size); grown files are appended at the end
of the image and the volume space size in the PVD is updated. The PS2 locates files with
sceCdSearchFile, which reads these directory records, so relocation is transparent.
"""
import struct, os

SECTOR = 2048


class Rec:
    def __init__(self, path, lba, size, rec_offset, is_dir):
        self.path, self.lba, self.size, self.rec_offset, self.is_dir = path, lba, size, rec_offset, is_dir

    def __repr__(self):
        return f"{self.path} lba={self.lba} size={self.size}"


def read_sector(f, lba, n=1):
    f.seek(lba * SECTOR)
    return f.read(n * SECTOR)


def walk(f):
    pvd = read_sector(f, 16)
    assert pvd[1:6] == b"CD001", "no PVD"
    vol_space = struct.unpack_from("<I", pvd, 80)[0]
    root = pvd[156:156 + 34]
    rlba = struct.unpack_from("<I", root, 2)[0]
    rsize = struct.unpack_from("<I", root, 10)[0]
    out = []

    def rec_dir(lba, size, prefix):
        data = read_sector(f, lba, (size + SECTOR - 1) // SECTOR)
        pos = 0
        while pos < size:
            ln = data[pos]
            if ln == 0:
                pos = (pos // SECTOR + 1) * SECTOR
                continue
            elba = struct.unpack_from("<I", data, pos + 2)[0]
            esize = struct.unpack_from("<I", data, pos + 10)[0]
            flags = data[pos + 25]
            nlen = data[pos + 32]
            name = data[pos + 33: pos + 33 + nlen]
            if name not in (b"\0", b"\1"):
                nm = name.decode("ascii").split(";")[0]
                path = prefix + nm
                is_dir = bool(flags & 2)
                out.append(Rec(path, elba, esize, lba * SECTOR + pos, is_dir))
                if is_dir:
                    rec_dir(elba, esize, path + "/")
            pos += ln

    rec_dir(rlba, rsize, "")
    return vol_space, out


def set_record(f, rec, lba, size):
    o = rec.rec_offset
    f.seek(o + 2)
    f.write(struct.pack("<I", lba) + struct.pack(">I", lba) + struct.pack("<I", size) + struct.pack(">I", size))
    rec.lba, rec.size = lba, size


def set_volume_space(f, sectors):
    for sec in (16,):
        f.seek(sec * SECTOR + 80)
        f.write(struct.pack("<I", sectors) + struct.pack(">I", sectors))


if __name__ == "__main__":
    import sys
    with open(sys.argv[1], "rb") as f:
        vs, recs = walk(f)
    print("volume sectors", vs, "file sectors", os.path.getsize(sys.argv[1]) // SECTOR)
    for r in sorted(recs, key=lambda r: r.lba):
        end = r.lba + (r.size + SECTOR - 1) // SECTOR
        print(f"{r.lba:8d} {end:8d} {r.size:11d} {'D' if r.is_dir else 'F'} {r.path}")
