import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chess_helper.core import data_dir, find_engine, save_settings, load_settings
from chess_helper.installer import install_stockfish


if __name__ == "__main__":
    path = find_engine()
    if not path:
        try:
            print("Downloading official Stockfish 19 (about 80 MB, first run only)...", flush=True)
            path = str(install_stockfish(data_dir() / "engine"))
            settings = load_settings()
            settings["engine"] = path
            save_settings(settings)
        except Exception as exc:
            print("Stockfish setup: " + str(exc), file=sys.stderr)
            print("The app will open; use its Engine tab to choose or install Stockfish.", file=sys.stderr)
    else:
        print("Using engine: " + path, flush=True)
