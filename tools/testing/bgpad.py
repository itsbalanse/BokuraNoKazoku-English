"""Background PCSX2 control from Python (same approach as bg.ps1, without PowerShell startup cost):
keys are posted to the PCSX2 game window, screenshots come from PCSX2's F8 hotkey, and all PCSX2
windows are kept parked off-screen. Never touches the foreground window or global input."""
import ctypes, ctypes.wintypes as wt, os, time, glob, shutil, subprocess

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPS = os.path.join(W, "emu", "PCSX2", "snaps")
SHOTS = os.path.join(W, "shots")
user32 = ctypes.windll.user32
VK = {"F2": 0x71, "F12": 0x7B, "F1": 0x70, "F3": 0x72, "Space": 0x20, "Up": 0x26, "Down": 0x28, "Left": 0x25, "Right": 0x27, "Return": 0x0D, "Tab": 0x09, "F8": 0x77, "Escape": 0x1B}
EXT = {0x25, 0x26, 0x27, 0x28}
EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


_pid = None


def pcsx2_pid():
    global _pid
    if _pid and user32.IsWindow(windows_any(_pid)):
        return _pid
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq pcsx2-qt.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        if "pcsx2-qt.exe" in line:
            _pid = int(line.split('","')[1])
            return _pid
    return None


def windows_any(pid):
    ws = windows(pid)
    return ws[0] if ws else 0


def windows(pid):
    res = []

    def cb(h, l):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(h):
            res.append(h)
        return True
    user32.EnumWindows(EnumProc(cb), 0)
    return res


def title(h):
    b = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(h, b, 256)
    return b.value


_last_park = 0


def park():
    global _last_park
    if time.time() - _last_park < 1.0:
        return
    _last_park = time.time()
    pid = pcsx2_pid()
    if not pid:
        return
    for h in windows(pid):
        r = wt.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        if r.left > -3000:
            user32.SetWindowPos(h, 1, -4000, 0, 0, 0, 0x0001 | 0x0010)  # NOSIZE | NOACTIVATE


def game_window():
    pid = pcsx2_pid()
    ws = windows(pid) if pid else []
    for h in ws:
        t = title(h)
        if t and not t.startswith("PCSX2"):
            return h
    return ws[0] if ws else None


def key(name, ms=120):
    h = game_window()
    vk = VK[name] if name in VK else ord(name.upper())
    sc = user32.MapVirtualKeyW(vk, 0)
    ext = 1 if vk in EXT else 0
    down = 1 | (sc << 16) | (ext << 24)
    up = down | (1 << 30) | (1 << 31)
    user32.PostMessageW(h, 0x0100, vk, down)
    time.sleep(ms / 1000)
    user32.PostMessageW(h, 0x0101, vk, ctypes.c_ssize_t(up).value)
    time.sleep(0.12)


def wait(ms):
    end = time.time() + ms / 1000
    while time.time() < end:
        park()
        time.sleep(min(0.25, max(0, end - time.time())))


def shot(name):
    before = set(glob.glob(os.path.join(SNAPS, "*")))
    key("F8", 80)
    for _ in range(60):
        time.sleep(0.15)
        new = set(glob.glob(os.path.join(SNAPS, "*"))) - before
        if new:
            src = new.pop()
            for _ in range(50):
                try:
                    time.sleep(0.15)
                    shutil.move(src, os.path.join(SHOTS, name + ".png"))
                    return os.path.join(SHOTS, name + ".png")
                except OSError:
                    pass
    return None
