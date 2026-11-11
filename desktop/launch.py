"""Standard-library bootstrap; accepts the macOS system Python just for setup."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def launch():
    os.chdir(ROOT)
    venv = ROOT / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    uv = shutil.which("uv")
    if not uv and Path("/opt/homebrew/bin/uv").is_file():
        uv = "/opt/homebrew/bin/uv"
    if not python.exists():
        print("Preparing BoardLens (first run only)...", flush=True)
        if uv:
            subprocess.run([uv, "venv", "--python", "3.12", str(venv)], check=True)
        elif sys.version_info >= (3, 10):
            subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        else:
            raise RuntimeError("Install Python 3.12 or newer from https://www.python.org/downloads/ and run this launcher again.")
    marker = venv / "boardlens-requirements.txt"
    requirements = ROOT / "requirements.txt"
    if not marker.exists() or marker.read_bytes() != requirements.read_bytes():
        print("Installing desktop and chess dependencies...", flush=True)
        args = [uv, "pip", "install", "--python", str(python)] if uv else [str(python), "-m", "pip", "install"]
        subprocess.run(args + ["-r", str(requirements)], check=True)
        marker.write_bytes(requirements.read_bytes())
    # Downloads only if no compatible UCI engine is already available.
    subprocess.run([str(python), str(ROOT / "tools" / "setup_engine.py")], check=True)
    print("Starting BoardLens...", flush=True)
    return subprocess.call([str(python), "-m", "chess_helper"])


if __name__ == "__main__":
    try:
        raise SystemExit(launch())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print("\nSetup could not finish: " + str(error), file=sys.stderr)
        print("See START-HERE.txt. Your existing project files were kept.", file=sys.stderr)
        raise SystemExit(1)
