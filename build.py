"""
Build script to generate standalone executable via PyInstaller.
"""

import sys
import os
import subprocess
from pathlib import Path

def build():
    print("Starting Smart Clinical Lab application build...")
    spec_file = Path(__file__).resolve().parent / "smart_lab.spec"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_file)
    ]

    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        dist_dir = Path(__file__).resolve().parent / "dist"
        print(f"\nBuild Succeeded! Output directory: {dist_dir}")
        for f in dist_dir.glob("*"):
            print(f" - {f.name}")
    else:
        print(f"\nBuild Failed with exit code {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build()
