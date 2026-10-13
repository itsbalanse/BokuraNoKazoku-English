# Background cold-boot test (no focus stealing): boot work\test.iso, start a new game
# (scenario A, preset names), skip the opening movie, then run extra bg.ps1 commands.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$cmds)
$w = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path   # repository root
& "$w\tools\bg.ps1" "launch:$w\test.iso" "wait:22000" "Return:150" "wait:2500" "C:150" "wait:7000" "C:150" "wait:3000" "C:150" "wait:2000" "C:150" "wait:2000" "C:150" "wait:1500" "C:150" "wait:1500" "C:150" "wait:1500" "C:150" "wait:1500" "C:150" "wait:5000" "Return:150" "wait:1500" @cmds
