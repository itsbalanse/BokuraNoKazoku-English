#!/bin/bash
# usage: run.sh OUTFILE (ref:HEX | fn:HEX)...
# Runs DecompXrefs.java on the MIPS64 analysis copy. Retries while the project lock from a
# previous JVM is still held (the run then exits without executing the script).
# set JAVA_HOME and GHIDRA_HOME for your machine, and GHIDRA_PROJECT to a folder holding the
# "bnk64" project with the MIPS64 analysis copy of the executable (see tools/ee2mips64.py)
: "${GHIDRA_HOME:?set GHIDRA_HOME}" "${GHIDRA_PROJECT:?set GHIDRA_PROJECT}"
HERE="$(cd "$(dirname "$0")" && pwd -W 2>/dev/null || pwd)"
cd "$(dirname "$0")"
out="$1"; shift
rm -f "$out"
for attempt in 1 2 3 4 5; do
  "$GHIDRA_HOME/support/analyzeHeadless" "$GHIDRA_PROJECT" bnk64 -process analysis_SCPS_150.88 -noanalysis -scriptPath "$HERE" -postScript DecompXrefs.java "$HERE/$out" "$@" > last_run.log 2>&1
  [ -s "$out" ] && break
  sleep 3
done
grep -i "exception" last_run.log | head -3
wc -l "$out"
