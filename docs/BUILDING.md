# Building the patch from source

You need your own copy of the game (the Redump dump listed in the README), Python 3 with Pillow and NumPy, and a C compiler (MinGW-w64 / gcc) for the compression library and the Windows tools.

## Layout

Place the files like this (the tools find each other relative to the repository folder):

```
<parent>/
  Bokura no Kazoku - My Family Growing Up in the 21st Century (Japan)/
      Bokura no Kazoku - My Family Growing Up in the 21st Century (Japan).iso
  BokuraNoKazoku-English/      <- this repository
      tools/ tl/ ...
```

## 1. Prepare

```bash
gcc -O2 -shared -o tools/lz.dll tools/lz.c      # XAP LZ codec (xap.py falls back to pure Python, slowly)
```

Extract the game files from your ISO into `extracted/DATA/` (each `X.XAP` becomes a folder of the same name) with `tools/xap.py`, and copy `FONT.XAP/font20.moj` to `font/font20.moj` (used for text-width measurements).

Generate the dialogue index from your own copy (this writes the Japanese script locally; it is not part of the repo):

```bash
python tools/events_extract.py
```

## 2. Build

```bash
python tools/shorten.py              # fit pass for list labels
python tools/layout_fit.py           # window layout fit pass
python tools/layout_fit.py --news    # Family News rewrap
python tools/txt_tl.py apply         # UI / database text -> build/mod
python tools/tex_tl.py all           # UI textures and portrait captions
python tools/tex_minig.py            # minigame textures
python tools/events_inject.py        # dialogue -> build/mod/EVENT.XAP
python tools/lint_codes.py           # sanity check of text control codes
python tools/build_all.py test.iso   # repack archives and rebuild the ISO
```

The executable (`SCPS_150.88`) changes come from the community `elfPatcher` tool (horizontal text + kerning) plus the save-title strings; place the patched executable in `build/loose/SCPS_150.88`.

## 3. Make the patch

```bash
python tools/mkpatch.py "<original>.iso" test.iso BokuraNoKazoku_English.bps
python patcher/bps.py BokuraNoKazoku_English.bps "<original>.iso" check.iso   # verify round trip
```

## File format notes

- **XAP archives:** `XAPF` header, a `FILE` chunk of 32-byte entries (name offset, flags (1 = LZ), data offset, raw/stored size, DOS date), then a `BODY` chunk with 16-byte-aligned entries.
- **LZ:** MSB-first control bits interleaved with data bytes; `0` = literal, `10` + byte = short match (or end), `11` + byte + 4 bits = long match; Elias-gamma lengths.
- **Dialogue (.mes):** a line starting with `[0-9A-Za-z]` begins a new label, `#` starts a comment, ASCII `,` is a page break, `$VAR$` inserts names, `@n` new line, `@sN` size, `@rN@gN@bN` colour, `@dN` horizontal offset. A digit directly after a control code merges into its argument, so lines starting with a digit are prefixed with `@d0 `.
- **Textures:** TIM2 (`.tm2`), 4/8-bit indexed with CSM1-swizzled CLUTs; sprite rectangles are defined in `texture.txt` / minigame `layout.txt`.
- The game finds files through the ISO9660 directory records, so files that grow are relocated into free space at the end of the image.
