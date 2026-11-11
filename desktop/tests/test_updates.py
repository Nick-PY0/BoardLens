

def test_automatic_queue_requires_current_hash_newer_version_and_opt_in(monkeypatch,tmp_path):
    import hashlib,json
    from chess_helper import updater
    monkeypatch.setattr(updater,'data_dir',lambda:tmp_path)
    folder=tmp_path/'updates';folder.mkdir();archive=folder/'automatic-update.zip';archive.write_bytes(b'queued-test-archive')
    marker=folder/'pending.json';value={'version':'99.0.0','sha256':hashlib.sha256(archive.read_bytes()).hexdigest()};marker.write_text(json.dumps(value))
    assert updater.pending_update()==archive
    updater.set_auto_enabled(False);assert updater.pending_update() is None and marker.exists()
    updater.set_auto_enabled(True);archive.write_bytes(b'corrupt')
    assert updater.pending_update() is None and not marker.exists()
