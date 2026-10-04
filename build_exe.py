"""
build_exe.py
Automated PyInstaller build script for creating a standalone Windows executable.
Includes all necessary hidden imports for Paramiko and Cryptography.
Copies config.json alongside the compiled FileInspector.exe.
"""
import os
import sys
import shutil
import subprocess

def build():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(base_dir, "main.py")
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")
    config_src = os.path.join(base_dir, "config.json")

    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=FileInspector",
        "--onefile",
        "--windowed",
        "--hidden-import=paramiko",
        "--hidden-import=cryptography",
        "--hidden-import=cffi",
        "--hidden-import=bcrypt",
        "--hidden-import=pynacl",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        "--clean",
        main_py
    ]

    print("Building standalone Windows executable with PyInstaller...")
    print("Command:", " ".join(cmd))
    res = subprocess.run(cmd)

    if res.returncode == 0:
        exe_path = os.path.join(dist_dir, "FileInspector.exe")
        print("\n[SUCCESS] Standalone executable created at:", exe_path)

        # Copy config.json to dist directory so it's ready alongside the executable
        if os.path.exists(config_src):
            config_dst = os.path.join(dist_dir, "config.json")
            shutil.copy2(config_src, config_dst)
            print("[INFO] Copied config.json alongside executable:", config_dst)
    else:
        print("\n[ERROR] Build failed with exit code:", res.returncode)

if __name__ == "__main__":
    build()
