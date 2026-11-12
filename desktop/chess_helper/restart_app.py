"""Restart through the real app launcher after the current process saves and exits."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time


def launcher_command(root, python=sys.executable):
    launcher = os.environ.get('BOARDLENS_NATIVE_LAUNCHER')
    if launcher and Path(launcher).exists():
        return ['/usr/bin/open', '-n', launcher] if sys.platform == 'darwin' else [launcher]
    return [python, str(Path(root) / 'launch.py')]


def restart_command(pid, root):
    return [sys.executable, str(Path(__file__).resolve()), '--pid', str(pid), '--root', str(root)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    for _ in range(200):
        try:
            os.kill(args.pid, 0)
        except OSError:
            break
        time.sleep(.1)
    else:
        return
    subprocess.Popen(launcher_command(args.root), cwd=args.root, start_new_session=True,
                     **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}))


if __name__ == '__main__':
    main()
