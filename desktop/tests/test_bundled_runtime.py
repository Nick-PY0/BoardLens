import launch
import pytest


def test_dependency_changes_cannot_mutate_a_signed_bundled_runtime(tmp_path, monkeypatch):
    app = tmp_path / 'source'
    app.mkdir()
    (app / 'requirements.txt').write_text('new dependency\n')
    runtime = tmp_path / 'sealed runtime'
    executable = runtime / 'bin/python3'
    executable.parent.mkdir(parents=True)
    executable.touch()
    marker = runtime / 'boardlens-requirements.txt'
    marker.write_text('old dependency\n')
    monkeypatch.setattr(launch, 'ROOT', app)
    monkeypatch.setenv('BOARDLENS_NATIVE_PYTHON', str(executable))
    monkeypatch.setenv('BOARDLENS_BUNDLED_RUNTIME', '1')
    calls = []
    monkeypatch.setattr(launch.subprocess, 'run', lambda *a, **kw: calls.append(a))
    with pytest.raises(RuntimeError, match='newer Mac installer'):
        launch.launch()
    assert not calls
    assert marker.read_text() == 'old dependency\n'
