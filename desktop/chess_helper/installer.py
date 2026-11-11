"""Pinned official releases; hashes are from GitHub's release asset manifest."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import platform
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile


RELEASE = "sf_19"
ASSETS = {
    "Darwin": ("stockfish-macos-universal.tar.gz", "a1f0e3bcc5a6927a11fe6fc8e54a779754645f3c2bae2cf13420fd1957adaa77", "stockfish-macos-universal"),
    "Windows": ("stockfish-windows-x86-64-universal.zip", "3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7", "stockfish-windows-x86-64-universal.exe"),
    "Windows-arm64": ("stockfish-windows-arm64-universal.zip", "8372ad3f0d7276deb2c70f801f541ec7db463219fc6d9c7592864e542aa4f401", "stockfish-windows-arm64-universal.exe"),
    "Linux": ("stockfish-linux-x86-64-universal.tar.gz", "9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f", "stockfish-linux-x86-64-universal"),
    "Linux-arm64": ("stockfish-linux-arm64-universal.tar.gz", "fe26cfd1d9db4c8af3d21e24d9ff34cacb31c1f940085a7583da11796f2bac01", "stockfish-linux-arm64-universal"),
}


def asset_for(system=None, machine=None):
    system, machine = system or platform.system(), (machine or platform.machine()).lower()
    key = system + "-arm64" if system != "Darwin" and machine in ("arm64", "aarch64") else system
    if key not in ASSETS or machine not in ("arm64", "aarch64", "amd64", "x86_64"):
        raise RuntimeError("Install a UCI engine manually for this operating system / CPU.")
    return ASSETS[key]


def verified_digest(path, expected):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise ValueError("Stockfish download checksum mismatch. No executable was installed.")


def install_stockfish(destination, archive_path=None):
    filename, expected, executable = asset_for()
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="boardlens-", dir=destination) as temporary:
        temporary = Path(temporary)
        archive = Path(archive_path) if archive_path else temporary / filename
        if archive_path is None:
            url = f"https://github.com/official-stockfish/Stockfish/releases/download/{RELEASE}/{filename}"
            request = urllib.request.Request(url, headers={"User-Agent": "BoardLens/1.0"})
            with urllib.request.urlopen(request, timeout=45) as response, archive.open("wb") as target:
                shutil.copyfileobj(response, target)
        verified_digest(archive, expected)
        # Extract just the verified binary. Never extract arbitrary archive paths.
        staged = temporary / executable
        if filename.endswith(".zip"):
            with zipfile.ZipFile(archive) as source:
                matches = [info for info in source.infolist() if Path(info.filename).name == executable and not info.is_dir()]
                if len(matches) != 1:
                    raise ValueError("The official archive has an unexpected binary layout.")
                with source.open(matches[0]) as handle, staged.open("wb") as target:
                    shutil.copyfileobj(handle, target)
        else:
            with tarfile.open(archive, "r:gz") as source:
                matches = [info for info in source.getmembers() if Path(info.name).name == executable and info.isfile()]
                if len(matches) != 1:
                    raise ValueError("The official archive has an unexpected binary layout.")
                with source.extractfile(matches[0]) as handle, staged.open("wb") as target:
                    shutil.copyfileobj(handle, target)
        staged.chmod(0o755)
        result = destination / executable
        os.replace(staged, result)
        return result
