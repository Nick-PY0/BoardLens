import hashlib,io,json,zipfile,threading
from pathlib import Path
import pytest
from chess_helper import updater,update_apply


def archive(path,files):
    files=dict(files);files['release-files.json']=json.dumps(list(files)+['release-files.json']).encode()
    with zipfile.ZipFile(path,'w') as out:
        for name,data in files.items():out.writestr('BoardLens/'+name,data)
    return path


def test_version_and_repository_pinning():
    assert updater.newer('2.12.0','2.11.0') and not updater.newer('2.9.0','2.11.0')
    for value in ['https://evil.test/Nick-PY0/BoardLens/releases/download/v1/a.zip','http://github.com/Nick-PY0/BoardLens/releases/download/v1/a.zip','https://github.com/other/repo/releases/download/v1/a.zip']:
        with pytest.raises(ValueError):updater.asset_url(value)
    with pytest.raises(ValueError):updater.newer('latest')


def test_release_requires_complete_stable_manifest(monkeypatch):
    base='https://github.com/Nick-PY0/BoardLens/releases/download/v1.0.0/'
    release={'assets':[{'name':'boardlens-update.json','browser_download_url':base+'boardlens-update.json'},{'name':updater.ASSET,'browser_download_url':base+updater.ASSET}]}
    manifest={'schema':1,'desktop':{'version':'2.12.0','asset':updater.ASSET,'sha256':'a'*64}}
    monkeypatch.setattr(updater,'read_url',lambda url,limit:json.dumps(release if url==updater.API else manifest).encode())
    assert updater.latest_release()['version']=='2.12.0'
    manifest['desktop']['sha256']='invalid'
    with pytest.raises(ValueError):updater.latest_release()
    manifest['desktop']['sha256']='a'*64;release['prerelease']=True
    with pytest.raises(ValueError):updater.latest_release()


def test_download_checksum_and_cancellation_leave_no_partial_files(tmp_path,monkeypatch):
    payload=b'update archive'
    monkeypatch.setattr(updater.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(payload))
    info={'url':'https://github.com/Nick-PY0/BoardLens/releases/download/v1/update.zip','sha256':'0'*64};target=tmp_path/'update.zip'
    with pytest.raises(ValueError,match='Checksum'):updater.download_update(info,target)
    assert list(tmp_path.iterdir())==[]
    info['sha256']=hashlib.sha256(payload).hexdigest();assert updater.download_update(info,target).read_bytes()==payload
    cancel=threading.Event();cancel.set()
    with pytest.raises(ValueError,match='cancelled'):updater.download_update(info,target,cancel)
    assert target.read_bytes()==payload and not target.with_suffix('.partial').exists()


def test_update_preserves_runtime_unknown_files_and_creates_rollback(tmp_path):
    root=tmp_path/'app';root.mkdir();(root/'.venv').mkdir();(root/'.venv/python').write_text('runtime');(root/'personal.txt').write_text('mine');(root/'old.py').write_text('old');(root/'obsolete.py').write_text('obsolete')
    (root/'release-files.json').write_text(json.dumps(['old.py','obsolete.py','release-files.json']))
    package=archive(tmp_path/'update.zip',{'old.py':b'new','chess_helper/new.py':b'new module'})
    backup=tmp_path/'backup';update_apply.apply_archive(package,root,backup)
    assert (root/'old.py').read_text()=='new' and not (root/'obsolete.py').exists()
    assert (root/'personal.txt').read_text()=='mine' and (root/'.venv/python').read_text()=='runtime'
    assert (backup/'old.py').read_text()=='old' and (backup/'obsolete.py').read_text()=='obsolete'


@pytest.mark.parametrize('name',['../outside','.venv/python','/absolute','a\\b','C:/outside'])
def test_archive_traversal_and_runtime_replacement_rejected(tmp_path,name):
    root=tmp_path/'app';root.mkdir();package=archive(tmp_path/'update.zip',{name:b'bad'})
    with pytest.raises(ValueError):update_apply.apply_archive(package,root,tmp_path/'backup')
    assert list(root.iterdir())==[]


def test_failed_install_rolls_back_every_changed_file(tmp_path,monkeypatch):
    root=tmp_path/'app';root.mkdir();(root/'first.py').write_text('original')
    package=archive(tmp_path/'update.zip',{'first.py':b'new','second.py':b'new'})
    original=update_apply.os.replace
    def fail(source,target):
        if Path(target).name=='second.py':raise OSError('Simulated write failure')
        return original(source,target)
    monkeypatch.setattr(update_apply.os,'replace',fail)
    with pytest.raises(OSError):update_apply.apply_archive(package,root,tmp_path/'backup')
    assert (root/'first.py').read_text()=='original' and not (root/'second.py').exists()
    assert not list(root.rglob('*.boardlens-update'))
