from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "code" / "delta05_diagnostic_runner.py"
LOGS = ROOT / "logs"
STDOUT = LOGS / "overnight_stdout.log"
STDERR = LOGS / "overnight_stderr.log"
PID_FILE = LOGS / "overnight_pid.txt"


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    out = STDOUT.open("ab", buffering=0)
    err = STDERR.open("ab", buffering=0)
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [sys.executable, "-u", str(RUNNER), "--mode", "all"],
        cwd=str(ROOT.parents[0]),
        stdout=out,
        stderr=err,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    PID_FILE.write_text(str(process.pid) + "\n", encoding="utf-8")
    print(process.pid)


if __name__ == "__main__":
    main()
