"""
build_exe.py
Automated PyInstaller build script for creating a standalone Windows executable.
Zero external runtime dependencies.
"""
import os
import sys
import subprocess

def build():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(base_dir, "main.py")
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=FileInspector",
        "--onefile",
        "--windowed",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        "--clean",
        main_py
    ]

    print("Building standalone Windows executable with PyInstaller...")
    print("Command:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\n[SUCCESS] Binary created at:", os.path.join(dist_dir, "FileInspector.exe"))
    else:
        print("\n[ERROR] Build failed with code:", res.returncode)

if __name__ == "__main__":
    build()
