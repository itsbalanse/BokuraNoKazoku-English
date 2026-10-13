/* "Play Bokura no Kazoku.exe": starts PCSX2 (in .\PCSX2) straight into the English ISO.
 * If the BIOS named in PCSX2\inis\PCSX2.ini is missing, the first file found in PCSX2\bios is
 * selected automatically, so players only have to drop in their own BIOS dump. */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

#define ISO_NAME L"Bokura no Kazoku (English).iso"
#define TITLE L"Bokura no Kazoku"

static void msg(const wchar_t *t) { MessageBoxW(NULL, t, TITLE, MB_ICONERROR); }

/* Make sure [Filenames] BIOS = <file> points at an existing file in PCSX2\bios. */
static int ensure_bios(const wchar_t *emu)
{
    wchar_t ini[MAX_PATH], pat[MAX_PATH], cur[MAX_PATH];
    char line[1024], name[MAX_PATH] = "";
    swprintf(ini, MAX_PATH, L"%ls\\inis\\PCSX2.ini", emu);
    FILE *f = _wfopen(ini, L"rb");
    if (!f) return 0;
    static char text[1 << 16]; size_t n = fread(text, 1, sizeof(text) - 1, f); fclose(f); text[n] = 0;
    char *p = strstr(text, "\nBIOS = ");
    if (p) sscanf(p + 8, "%259[^\r\n]", name);
    if (name[0]) {
        swprintf(cur, MAX_PATH, L"%ls\\bios\\%hs", emu, name);
        if (GetFileAttributesW(cur) != INVALID_FILE_ATTRIBUTES) return 1;
    }
    WIN32_FIND_DATAW fd;
    swprintf(pat, MAX_PATH, L"%ls\\bios\\*", emu);
    HANDLE h = FindFirstFileW(pat, &fd);
    char found[MAX_PATH] = "";
    if (h != INVALID_HANDLE_VALUE) {
        do {
            if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) && fd.nFileSizeLow >= 512 * 1024) {
                WideCharToMultiByte(CP_UTF8, 0, fd.cFileName, -1, found, MAX_PATH, NULL, NULL);
                break;
            }
        } while (FindNextFileW(h, &fd));
        FindClose(h);
    }
    if (!found[0]) return 0;
    /* rewrite the BIOS line (or add it under [Filenames]) */
    static char out[1 << 16];
    if (p) {
        char *eol = strpbrk(p + 1, "\r\n"); if (!eol) eol = text + n;
        snprintf(out, sizeof(out), "%.*s\nBIOS = %s%s", (int)(p - text), text, found, eol);
    } else {
        char *s = strstr(text, "[Filenames]");
        if (s) { s += 11; snprintf(out, sizeof(out), "%.*s\r\nBIOS = %s%s", (int)(s - text), text, found, s); }
        else snprintf(out, sizeof(out), "%s\r\n[Filenames]\r\nBIOS = %s\r\n", text, found);
    }
    f = _wfopen(ini, L"wb"); if (!f) return 0;
    fwrite(out, 1, strlen(out), f); fclose(f);
    return 1;
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE prev, PWSTR args, int show)
{
    wchar_t dir[MAX_PATH], exe[MAX_PATH], iso[MAX_PATH], emu[MAX_PATH], cmd[4 * MAX_PATH];
    GetModuleFileNameW(NULL, dir, MAX_PATH);
    wchar_t *slash = wcsrchr(dir, L'\\');
    if (slash) *slash = 0;
    swprintf(emu, MAX_PATH, L"%ls\\PCSX2", dir);
    swprintf(exe, MAX_PATH, L"%ls\\pcsx2-qt.exe", emu);
    swprintf(iso, MAX_PATH, L"%ls\\%ls", dir, ISO_NAME);
    if (GetFileAttributesW(exe) == INVALID_FILE_ATTRIBUTES) {
        msg(L"PCSX2 was not found.\n\nDownload the Windows portable build of PCSX2 from pcsx2.net and "
            L"extract it into the \"PCSX2\" folder next to this launcher (so that PCSX2\\pcsx2-qt.exe exists).");
        return 1;
    }
    if (GetFileAttributesW(iso) == INVALID_FILE_ATTRIBUTES) {
        msg(L"\"" ISO_NAME L"\" was not found next to this launcher.\n\n"
            L"Create it with the patcher from your own copy of the game, then put it in this folder.");
        return 1;
    }
    if (!ensure_bios(emu)) {
        msg(L"No PS2 BIOS found.\n\nPut a BIOS dump from your own PlayStation 2 into the PCSX2\\bios folder.");
        return 1;
    }
    /* -batch: close PCSX2 when the game is closed; -fullscreen: start fullscreen (F11 toggles) */
    swprintf(cmd, 4 * MAX_PATH, L"\"%ls\" -batch -fullscreen %ls -- \"%ls\"", exe, args ? args : L"", iso);
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    if (!CreateProcessW(exe, cmd, NULL, NULL, FALSE, 0, NULL, emu, &si, &pi)) {
        msg(L"Could not start PCSX2.");
        return 1;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}
