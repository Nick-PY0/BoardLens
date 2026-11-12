"""Standard-library bootstrap; accepts the macOS system Python just for setup."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def launch():
    from chess_helper.processes import windowless_children
    windowless_children()
    os.chdir(ROOT)
    venv = ROOT / ".venv"
    native=os.environ.get('BOARDLENS_NATIVE_PYTHON')
    python = Path(native) if native else venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
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
    marker = (Path(native).parent.parent if native and os.name!="nt" else Path(native).parent if native else venv) / "boardlens-requirements.txt"
    requirements = ROOT / "requirements.txt"
    if not marker.exists() or marker.read_bytes() != requirements.read_bytes():
        if os.environ.get('BOARDLENS_BUNDLED_RUNTIME'):
            raise RuntimeError('This update needs a newer Mac installer. Download the latest BoardLens app; your saved settings and engines will stay saved.')
        print("Installing desktop and chess dependencies...", flush=True)
        args = [uv, "pip", "install", "--python", str(python)] if uv and not native else [str(python), "-m", "pip", "install"]
        subprocess.run(args + ["-r", str(requirements)], check=True)
        marker.write_bytes(requirements.read_bytes())
    # Downloads only if no compatible UCI engine is already available.
    engine=os.environ.get('STOCKFISH_EXECUTABLE','')
    if not (native and engine and Path(engine).is_file()):
        subprocess.run([str(python), str(ROOT / "tools" / "setup_engine.py")], check=True)
    print("Starting BoardLens...", flush=True)
    if native:
        if os.environ.get('BOARDLENS_EMBEDDED_PYTHON'):
            import runpy
            runpy.run_module('chess_helper',run_name='__main__')
            return 0
        os.execv(str(python),[str(python),"-m","chess_helper"])
    return subprocess.call([str(python), "-m", "chess_helper"])


if __name__ == "__main__":
    try:
        raise SystemExit(launch())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print("\nSetup could not finish: " + str(error), file=sys.stderr)
        print("See START-HERE.txt. Your existing project files were kept.", file=sys.stderr)
        raise SystemExit(1)
