# Drive PCSX2 entirely in the background: no focus stealing, no global keystrokes.
# Keys are posted straight to the PCSX2 game window; screenshots use PCSX2's own
# screenshot hotkey (F8), so only the game frame is captured. All PCSX2 windows are
# parked off-screen so they never cover the desktop.
# Usage: bg.ps1 [launch:ISO] "Return:120" "wait:800" "shot:name" "X:100*5" ... [kill]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$cmds)

Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class BG {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint c, uint t);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  public static List<IntPtr> Windows(uint pid) {
    var res = new List<IntPtr>();
    EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p); if (p == pid && IsWindowVisible(h)) res.Add(h); return true; }, IntPtr.Zero);
    return res;
  }
  public static string Title(IntPtr h) { var s = new StringBuilder(256); GetWindowText(h, s, 256); return s.ToString(); }
  // park off-screen, bottom of z-order, never activate
  public static void Park(IntPtr h) {
    RECT r; GetWindowRect(h, out r);
    if (r.L > -3000) SetWindowPos(h, (IntPtr)1, -4000, 0, 0, 0, 0x0001 | 0x0010);  // NOSIZE|NOACTIVATE
  }
}
"@

$w = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path   # repository root
$exe = "$w\emu\PCSX2\pcsx2-qt.exe"
$snaps = "$w\emu\PCSX2\snaps"
$shots = "$w\shots"
New-Item -ItemType Directory -Force $shots, $snaps | Out-Null

$vk = @{ Up = 0x26; Down = 0x28; Left = 0x25; Right = 0x27; Return = 0x0D; Tab = 0x09; Space = 0x20;
  F1 = 0x70; F2 = 0x71; F3 = 0x72; F8 = 0x77; Escape = 0x1B; Backspace = 0x08 }
function Get-VK($k) { if ($vk.ContainsKey($k)) { return $vk[$k] } return [int][char]$k.ToUpper() }
$ext = @(0x25, 0x26, 0x27, 0x28)

function Get-Proc { Get-Process pcsx2-qt -ErrorAction SilentlyContinue | Select-Object -First 1 }
function Park-All {
  $p = Get-Proc; if (-not $p) { return }
  foreach ($h in [BG]::Windows([uint32]$p.Id)) { [BG]::Park($h) }
}
# The game window is the visible PCSX2 window whose title is the game (not the main/list window).
function Get-GameWin {
  $p = Get-Proc; if (-not $p) { throw "PCSX2 not running" }
  $ws = [BG]::Windows([uint32]$p.Id)
  $game = $ws | Where-Object { $t = [BG]::Title($_); $t -and $t -notmatch '^PCSX2' } | Select-Object -First 1
  if (-not $game) { $game = $ws | Select-Object -First 1 }
  return $game
}
function Key($name, $ms) {
  $h = Get-GameWin
  $v = Get-VK $name; $s = [BG]::MapVirtualKey($v, 0)
  $e = 0; if ($ext -contains $v) { $e = 1 }
  $down = 1 -bor ($s -shl 16) -bor ($e -shl 24)
  $up = $down -bor (1 -shl 30) -bor ([int64]1 -shl 31)
  [BG]::PostMessage($h, 0x0100, [IntPtr]$v, [IntPtr]$down) | Out-Null
  Start-Sleep -Milliseconds $ms
  [BG]::PostMessage($h, 0x0101, [IntPtr]$v, [IntPtr][int64]$up) | Out-Null
  Start-Sleep -Milliseconds 120
}

foreach ($c in $cmds) {
  $parts = $c.Split(':', 2)
  $name = $parts[0]; $arg = if ($parts.Count -gt 1) { $parts[1] } else { "100" }
  switch ($name) {
    "launch" {
      Get-Process pcsx2-qt -ErrorAction SilentlyContinue | Stop-Process -Force
      Start-Sleep -Milliseconds 800
      Start-Process -FilePath $exe -ArgumentList @("-batch", "-fastboot", "--", $arg) -WindowStyle Minimized
      # keep parking windows as they appear during startup
      for ($i = 0; $i -lt 100; $i++) { Park-All; Start-Sleep -Milliseconds 50 }
    }
    "kill" { Get-Process pcsx2-qt -ErrorAction SilentlyContinue | Stop-Process -Force }
    "wait" {
      $end = (Get-Date).AddMilliseconds([int]$arg)
      while ((Get-Date) -lt $end) { Park-All; Start-Sleep -Milliseconds 250 }
    }
    "shot" {
      $before = @(Get-ChildItem $snaps -File | ForEach-Object FullName)
      Key "F8" 80
      $new = $null
      for ($i = 0; $i -lt 40 -and -not $new; $i++) {
        Start-Sleep -Milliseconds 150
        $new = Get-ChildItem $snaps -File | Where-Object { $before -notcontains $_.FullName } | Select-Object -First 1
      }
      if ($new) {
        $ok = $false
        for ($i = 0; $i -lt 50 -and -not $ok; $i++) {
          Start-Sleep -Milliseconds 200
          try { Move-Item -Force $new.FullName (Join-Path $shots "$arg.png") -ErrorAction Stop; $ok = $true } catch {}
        }
        if ($ok) { Write-Output "shot $arg" } else { Write-Output "shot $arg FAILED (busy)" }
      } else { Write-Output "shot $arg FAILED" }
    }
    default {
      $ms = 100; $n = 1
      if ($arg -match '^(\d+)\*(\d+)$') { $ms = [int]$Matches[1]; $n = [int]$Matches[2] } elseif ($arg -match '^\d+$') { $ms = [int]$arg }
      for ($i = 0; $i -lt $n; $i++) { Key $name $ms }
    }
  }
}
