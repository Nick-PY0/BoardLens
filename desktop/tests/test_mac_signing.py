import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest


spec = importlib.util.spec_from_file_location('mac_signing', Path(__file__).parents[1] / 'packaging/mac_signing.py')
signing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signing)


def test_reuses_the_single_local_developer_identity(monkeypatch):
    fingerprint = 'A' * 40
    monkeypatch.setattr(signing.subprocess, 'run', lambda *a, **kw: SimpleNamespace(
        stdout=f'  1) {fingerprint} "Developer ID Application: Example (TEAM123)"\n'))
    assert signing.signing_identity() == fingerprint
    assert signing.signing_identity('chosen certificate') == 'chosen certificate'


def test_multiple_developer_identities_require_a_choice(monkeypatch):
    monkeypatch.setattr(signing.subprocess, 'run', lambda *a, **kw: SimpleNamespace(
        stdout='\n'.join(f'{n}) {str(n) * 40} "Developer ID Application: Example"' for n in (1, 2))))
    with pytest.raises(RuntimeError, match='several'):
        signing.signing_identity()


def test_unsigned_ci_is_labelled_and_never_uses_a_fake_identity(monkeypatch):
    calls = []
    monkeypatch.setattr(signing.subprocess, 'run', lambda command, **kw: (
        calls.append(command) or SimpleNamespace(stdout='0 valid identities found')))
    monkeypatch.setattr(signing.subprocess, 'check_output', lambda *a, **kw: 'designated => cdhash H"123"')
    identity = signing.signing_identity()
    assert identity == '-'
    result = signing.sign_app('BoardLens.app', identity)
    assert result['kind'] == 'ad-hoc'
    assert '--timestamp' not in calls[1]


def test_developer_builds_use_secure_timestamp(monkeypatch):
    calls = []
    monkeypatch.setattr(signing.subprocess, 'run', lambda command, **kw: calls.append(command))
    monkeypatch.setattr(signing.subprocess, 'check_output', lambda *a, **kw: 'designated => stable certificate')
    assert signing.sign_app('BoardLens.app', 'certificate')['kind'] == 'developer-id'
    assert '--timestamp' in calls[0]
    assert calls[1][1:4] == ['--verify', '--strict', 'BoardLens.app']
