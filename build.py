#!/usr/bin/env python3
import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    app_dir = Path(__file__).resolve().parent
    app_file = app_dir / "app.py"

    if not app_file.exists():
        print(f"Missing app file: {app_file}", file=sys.stderr)
        return 1

    system = platform.system().lower()
    machine = platform.machine().lower().replace(" ", "_")
    target = f"{system}_{machine}"

    dist_path = app_dir / "dist" / target
    work_path = app_dir / "build" / target
    spec_path = app_dir / "build" / "spec"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "TrajectoryCropGIF",
        "--distpath",
        str(dist_path),
        "--workpath",
        str(work_path),
        "--specpath",
        str(spec_path),
        str(app_file),
    ]

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=app_dir)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
