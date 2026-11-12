import shutil,zipfile,hashlib,os
import pytest
from chess_helper import lc0_support as lc0,engine_library

def test_optional_lc0_archive_is_verified_and_command_uses_its_network(monkeypatch,tmp_path):
    network=b'test network data';archive=tmp_path/'download.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('lc0.exe' if os.name=='nt' else 'lc0',b'engine');z.writestr(lc0.NETWORK,network)
    monkeypatch.setattr(lc0,'data_dir',lambda:tmp_path)
    monkeypatch.setattr(lc0.platform,'system',lambda:'Windows' if os.name=='nt' else 'Darwin')
    monkeypatch.setattr(lc0,'NETWORK_HASH',hashlib.sha256(network).hexdigest())
    monkeypatch.setattr(engine_library,'fetch',lambda url,target,*args:shutil.copyfile(archive,target))
    assert not lc0.available();lc0.install();assert lc0.available()
    command=lc0.command();assert command[0].endswith('lc0.exe' if os.name=='nt' else '/lc0') and '--backend=blas' in command
    assert '--weights='+str(lc0.folder()/lc0.NETWORK) in command

def test_lc0_rejects_mismatched_network_before_marking_ready(monkeypatch,tmp_path):
    archive=tmp_path/'download.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('lc0.exe' if os.name=='nt' else 'lc0',b'engine');z.writestr(lc0.NETWORK,b'bad network')
    monkeypatch.setattr(lc0,'data_dir',lambda:tmp_path)
    monkeypatch.setattr(lc0.platform,'system',lambda:'Windows' if os.name=='nt' else 'Darwin')
    monkeypatch.setattr(engine_library,'fetch',lambda url,target,*args:shutil.copyfile(archive,target))
    with pytest.raises(ValueError,match='expected engine and network'):lc0.install()
    assert not lc0.available()
