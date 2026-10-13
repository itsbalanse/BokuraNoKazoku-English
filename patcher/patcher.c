/* Bokura no Kazoku English patcher: applies BokuraNoKazoku_English.bps (next to this exe) to
 * the player's own Japanese ISO and writes "Bokura no Kazoku (English).iso".
 * Usage: double-click (a file picker opens), drag the ISO onto the exe, or
 *        patcher.exe ORIGINAL.iso [OUTPUT.iso]
 * Implements the BPS format (SourceRead/TargetRead/SourceCopy/TargetCopy) with CRC32 checks,
 * streaming so multi-GB images need little memory. */
#define _FILE_OFFSET_BITS 64
#include <windows.h>
#include <commdlg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <wchar.h>

static uint32_t crc_table[256];
static void crc_init(void) {
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t c = i;
        for (int k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320u ^ (c >> 1) : c >> 1;
        crc_table[i] = c;
    }
}
static uint32_t crc32_update(uint32_t crc, const uint8_t *p, size_t n) {
    crc = ~crc;
    while (n--) crc = crc_table[(crc ^ *p++) & 0xFF] ^ (crc >> 8);
    return ~crc;
}

static int gui;  /* popups only when started without arguments (double-click) */
static void fail(const char *msg) {
    fprintf(stderr, "\nERROR: %s\n", msg);
    if (gui) MessageBoxA(NULL, msg, "Bokura no Kazoku patcher", MB_ICONERROR);
    exit(1);
}

static uint8_t *patch; static size_t plen, ppos;
static uint64_t vint(void) {
    uint64_t data = 0, shift = 1;
    for (;;) {
        if (ppos >= plen) fail("patch file is truncated");
        uint8_t x = patch[ppos++];
        data += (x & 0x7F) * shift;
        if (x & 0x80) return data;
        shift <<= 7; data += shift;
    }
}

#define BUF (1 << 22)
static uint8_t buf[BUF];

int wmain(int argc, wchar_t **argv) {
    crc_init();
    wchar_t dir[MAX_PATH], ppath[MAX_PATH], src[MAX_PATH] = L"", dst[MAX_PATH];
    GetModuleFileNameW(NULL, dir, MAX_PATH);
    wchar_t *sl = wcsrchr(dir, L'\\'); if (sl) *sl = 0;
    swprintf(ppath, MAX_PATH, L"%ls\\BokuraNoKazoku_English.bps", dir);

    printf("Bokura no Kazoku - English translation patcher\n\n");
    gui = argc < 2;
    if (argc > 1) wcsncpy(src, argv[1], MAX_PATH - 1);
    else {
        OPENFILENAMEW ofn = { sizeof(ofn) };
        ofn.lpstrFilter = L"PS2 disc image (*.iso)\0*.iso\0All files\0*.*\0";
        ofn.lpstrFile = src; ofn.nMaxFile = MAX_PATH;
        ofn.lpstrTitle = L"Select your Japanese Bokura no Kazoku ISO (SCPS-15088)";
        ofn.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST;
        if (!GetOpenFileNameW(&ofn)) return 0;
    }
    if (argc > 2) wcsncpy(dst, argv[2], MAX_PATH - 1);
    else {
        wcscpy(dst, src);
        wchar_t *s = wcsrchr(dst, L'\\');
        swprintf(s ? s + 1 : dst, MAX_PATH - (s ? (s + 1 - dst) : 0), L"Bokura no Kazoku (English).iso");
    }
    if (_wcsicmp(src, dst) == 0) fail("Output would overwrite the input ISO.");

    FILE *pf = _wfopen(ppath, L"rb");
    if (!pf) fail("BokuraNoKazoku_English.bps was not found next to the patcher.");
    fseek(pf, 0, SEEK_END); plen = ftell(pf); fseek(pf, 0, SEEK_SET);
    patch = malloc(plen);
    if (fread(patch, 1, plen, pf) != plen) fail("could not read the patch file");
    fclose(pf);
    if (plen < 16 || memcmp(patch, "BPS1", 4)) fail("not a BPS patch");
    uint32_t pcrc; memcpy(&pcrc, patch + plen - 4, 4);
    if (crc32_update(0, patch, plen - 4) != pcrc) fail("the patch file is corrupt (re-download it)");
    uint32_t want_src, want_tgt;
    memcpy(&want_src, patch + plen - 12, 4); memcpy(&want_tgt, patch + plen - 8, 4);

    ppos = 4;
    uint64_t ssize = vint(), tsize = vint(), msize = vint();
    ppos += msize;

    FILE *in = _wfopen(src, L"rb");
    if (!in) fail("could not open the ISO");
    _fseeki64(in, 0, SEEK_END);
    if ((uint64_t)_ftelli64(in) != ssize)
        fail("This ISO has the wrong size. You need the Redump dump of\n"
             "Bokura no Kazoku (Japan) SCPS-15088, CRC32 9D389B7C.");
    printf("Checking your ISO (CRC32)...\n");
    _fseeki64(in, 0, SEEK_SET);
    uint32_t c = 0; size_t n;
    while ((n = fread(buf, 1, BUF, in)) > 0) c = crc32_update(c, buf, n);
    if (c != want_src)
        fail("This ISO does not match the expected dump (CRC32 9D389B7C).\n"
             "Use an unmodified Redump dump of Bokura no Kazoku (Japan) SCPS-15088.");

    FILE *out = _wfopen(dst, L"w+b");
    if (!out) fail("could not create the output ISO");
    printf("Writing %ls\n", dst);
    uint64_t opos = 0, src_rel = 0, tgt_rel = 0, last = 0;
    uint32_t tc = 0;
    size_t end = plen - 12;
    while (ppos < end) {
        uint64_t d = vint(), len = (d >> 2) + 1;
        int cmd = d & 3;
        if (cmd == 0 || cmd == 2) {
            if (cmd == 2) {
                uint64_t o = vint();
                src_rel += (o & 1) ? -(int64_t)(o >> 1) : (int64_t)(o >> 1);
                _fseeki64(in, src_rel, SEEK_SET); src_rel += len;
            } else _fseeki64(in, opos, SEEK_SET);
            uint64_t left = len;
            while (left) {
                size_t k = left > BUF ? BUF : (size_t)left;
                if (fread(buf, 1, k, in) != k) fail("read error on the ISO");
                fwrite(buf, 1, k, out); tc = crc32_update(tc, buf, k); left -= k;
            }
        } else if (cmd == 1) {
            if (ppos + len > end) fail("patch file is truncated");
            fwrite(patch + ppos, 1, len, out); tc = crc32_update(tc, patch + ppos, len); ppos += len;
        } else {
            uint64_t o = vint();
            tgt_rel += (o & 1) ? -(int64_t)(o >> 1) : (int64_t)(o >> 1);
            for (uint64_t i = 0; i < len; i++) {
                uint8_t b;
                fflush(out); _fseeki64(out, tgt_rel++, SEEK_SET); fread(&b, 1, 1, out);
                _fseeki64(out, opos + i, SEEK_SET); fwrite(&b, 1, 1, out); tc = crc32_update(tc, &b, 1);
            }
        }
        opos += len;
        if (opos - last > (200ull << 20)) { last = opos; printf("  %llu%%\n", opos * 100 / tsize); }
    }
    fclose(out); fclose(in);
    if (opos != tsize || tc != want_tgt) {
        _wremove(dst);
        fail("The patched ISO failed its final check and was deleted.");
    }
    printf("\nDone! Created and verified:\n%ls\n", dst);
    if (gui) MessageBoxW(NULL, L"Done! \"Bokura no Kazoku (English).iso\" was created next to your original ISO.",
                L"Bokura no Kazoku patcher", MB_ICONINFORMATION);
    return 0;
}
