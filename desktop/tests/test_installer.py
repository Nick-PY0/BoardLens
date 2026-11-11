from pathlib import Path

import pytest

from chess_helper.installer import asset_for, verified_digest


def test_windows_and_mac_architecture_choices():
    assert asset_for("Windows", "AMD64")[0].endswith("x86-64-universal.zip")
    assert "arm64" in asset_for("Windows", "ARM64")[0]
    assert asset_for("Darwin", "arm64")[0] == asset_for("Darwin", "x86_64")[0]
    with pytest.raises(RuntimeError):
        asset_for("Windows", "i386")


def test_corrupt_download_rejected(tmp_path):
    path = tmp_path / "archive"
    path.write_bytes(b"not an official engine")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verified_digest(path, "0" * 64)
