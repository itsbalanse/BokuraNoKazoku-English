/* LZ codec for Bokura no Kazoku XAP archives (see xap.py for the format description).
 * Build: gcc -O2 -shared -o lz.dll lz.c
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define MAXOFF 0x10FF
#define MAXLEN 0x10000

typedef struct { const uint8_t *d; size_t n, pos; uint8_t cur, mask; } BR;

static int br_bit(BR *r, int *err) {
    if (r->mask == 0) {
        if (r->pos >= r->n) { *err = 1; return 0; }
        r->cur = r->d[r->pos++]; r->mask = 0x80;
    }
    int b = (r->cur & r->mask) ? 1 : 0;
    r->mask >>= 1;
    return b;
}

/* returns output length, or -1 on error */
__declspec(dllexport) long lz_decompress(const uint8_t *src, size_t n, uint8_t *dst, size_t cap) {
    BR r = { src, n, 1, n ? src[0] : 0, 0x80 };
    int err = 0;
    size_t o = 0;
    if (n == 0) return -1;
    for (;;) {
        if (!br_bit(&r, &err)) {
            if (err || r.pos >= n || o >= cap) return -1;
            dst[o++] = src[r.pos++];
            continue;
        }
        long off;
        if (!br_bit(&r, &err)) {
            if (err || r.pos >= n) return -1;
            int b = src[r.pos++];
            if (b == 0) break;
            off = b - 256;
        } else {
            if (err || r.pos >= n) return -1;
            int b = src[r.pos++];
            int x = 0;
            for (int i = 0; i < 4; i++) x = x * 2 + br_bit(&r, &err);
            off = ((b << 4) | x) - MAXOFF;
        }
        long g = 1;
        while (br_bit(&r, &err)) { g = g * 2 + br_bit(&r, &err); if (err) return -1; }
        if (err) return -1;
        long s = (long)o + off;
        if (s < 0 || o + g + 1 > cap) return -1;
        for (long i = 0; i <= g; i++) dst[o + i] = dst[s + i];
        o += g + 1;
    }
    return (long)o;
}

typedef struct { uint8_t *d; size_t o, cap, flag; uint8_t mask; } BW;

static void bw_bit(BW *w, int b) {
    if (w->mask == 0) { w->flag = w->o; w->d[w->o++] = 0; w->mask = 0x80; }
    if (b) w->d[w->flag] |= w->mask;
    w->mask >>= 1;
}
static void bw_byte(BW *w, uint8_t b) { w->d[w->o++] = b; }

static int gamma_len(long g) { /* bits for gamma code of g>=1 */
    int nb = 0; while ((g >> nb) > 1) nb++; return nb * 2 + 1;
}
static void bw_gamma(BW *w, long g) {
    int nb = 0; while ((g >> nb) > 1) nb++;
    for (int i = nb - 1; i >= 0; i--) { bw_bit(w, 1); bw_bit(w, (g >> i) & 1); }
    bw_bit(w, 0);
}

/* Optimal parse. dst must hold at least n + n/8 + 16 bytes. Returns compressed size. */
__declspec(dllexport) long lz_compress(const uint8_t *src, size_t n, uint8_t *dst) {
    uint32_t *cost = malloc((n + 1) * sizeof(uint32_t));
    int32_t *clen = malloc((n + 1) * sizeof(int32_t));
    int32_t *coff = malloc((n + 1) * sizeof(int32_t));
    /* hash chains over 2-byte prefixes */
    int32_t *head = malloc(65536 * sizeof(int32_t));
    int32_t *prev = malloc((n + 1) * sizeof(int32_t));
    for (int i = 0; i < 65536; i++) head[i] = -1;
    for (size_t i = 0; i + 1 < n; i++) {
        int h = src[i] | (src[i + 1] << 8);
        prev[i] = head[h]; head[h] = (int32_t)i;
    }
    cost[n] = 0;
    for (long i = (long)n - 1; i >= 0; i--) {
        uint32_t best = 9 + cost[i + 1];
        int32_t bl = 0, bo = 0;
        if ((size_t)i + 1 < n) {
            /* prev[] chains run nearest-first through earlier positions, and nearer offsets are
               never more expensive, so a farther candidate only matters for lengths beyond the
               longest match already seen. */
            long seen = 1;
            for (int32_t p = prev[i]; p >= 0 && i - p <= MAXOFF; p = prev[p]) {
                long maxl = (long)n - i; if (maxl > MAXLEN) maxl = MAXLEN;
                long l = 0;
                while (l < maxl && src[p + l] == src[i + l]) l++;
                if (l <= seen) continue;
                long off = p - i;
                int base = (off >= -255) ? 10 : 14;
                long from = seen + 1;
                for (long L = from; L <= l; L++) {
                    /* bound work on very long runs: dense near the top, sparse below */
                    if (l - L > 256 && (L & (L - 1)) != 0 && L != from) continue;
                    uint32_t c = base + gamma_len(L - 1) + cost[i + L];
                    if (c < best) { best = c; bl = (int32_t)L; bo = (int32_t)off; }
                }
                seen = l;
                if (l == maxl) break;
            }
        }
        cost[i] = best; clen[i] = bl; coff[i] = bo;
    }
    BW w = { dst, 0, 0, 0, 0 };
    size_t i = 0;
    while (i < n) {
        if (clen[i] == 0) { bw_bit(&w, 0); bw_byte(&w, src[i]); i++; continue; }
        long off = coff[i], L = clen[i];
        bw_bit(&w, 1);
        if (off >= -255) { bw_bit(&w, 0); bw_byte(&w, (uint8_t)(off + 256)); }
        else {
            long v = off + MAXOFF;
            bw_bit(&w, 1); bw_byte(&w, (uint8_t)(v >> 4));
            for (int k = 3; k >= 0; k--) bw_bit(&w, (v >> k) & 1);
        }
        bw_gamma(&w, L - 1);
        i += L;
    }
    bw_bit(&w, 1); bw_bit(&w, 0); bw_byte(&w, 0);
    free(cost); free(clen); free(coff); free(head); free(prev);
    return (long)w.o;
}
