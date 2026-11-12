"""Explicit optional LC0 CPU download, shared Mac/Windows command and fixed hashes."""
from pathlib import Path
import hashlib,os,platform,tempfile,zipfile,shutil
from .core import data_dir
VERSION='0.32.1'
NETWORK='791556.pb.gz'
NETWORK_HASH='b1c7047582a8ad37620849bf328935cb46f2ccbbecb7f2696c30c6b913ed690d'
WINDOWS_URL='https://github.com/LeelaChessZero/lc0/releases/download/v0.32.1/lc0-v0.32.1-windows-cpu-openblas.zip'
WINDOWS_HASH='b2caa8443f0e0cb15cf76c335c53985f2973cd6438e77d3e2366cd21d2effa38'
MAC_URL='https://github.com/Nick-PY0/BoardLens/releases/download/engine-addons-v1/BoardLens-LC0-Mac-Universal.zip'
MAC_HASH='8f5b6e38169ef8a68b13585799409dda869b7c630d3a9ebda0e6a1c853e3c97a'
def folder():return data_dir()/'lc0'
def executable():return folder()/('lc0.exe' if os.name=='nt' else 'lc0')
def available():return executable().is_file() and (folder()/NETWORK).is_file() and (folder()/'verified.txt').is_file()
def install():
    from .engine_library import fetch
    system=platform.system()
    if system not in ('Darwin','Windows'):raise ValueError('For this system, install LC0 manually and select Custom UCI.')
    with tempfile.TemporaryDirectory(prefix='boardlens-lc0-',dir=data_dir()) as temp:
        root=Path(temp);archive=root/'lc0.zip';fetch(WINDOWS_URL if system=='Windows' else MAC_URL,archive,'sha256',WINDOWS_HASH if system=='Windows' else MAC_HASH)
        target=root/'ready';target.mkdir()
        with zipfile.ZipFile(archive) as z:
            for entry in z.infolist():
                if entry.is_dir():continue
                name=Path(entry.filename)
                if name.is_absolute() or '..' in name.parts:raise ValueError('Invalid LC0 archive')
                if len(name.parts)!=1:raise ValueError('Unexpected LC0 archive layout')
                (target/name).write_bytes(z.read(entry))
        binary=target/('lc0.exe' if system=='Windows' else 'lc0');weights=target/NETWORK
        if not binary.is_file() or not weights.is_file() or hashlib.sha256(weights.read_bytes()).hexdigest()!=NETWORK_HASH:raise ValueError('LC0 archive did not contain the expected engine and network')
        if system!='Windows':binary.chmod(0o755)
        (target/'verified.txt').write_text(VERSION+'\n'+NETWORK_HASH+'\n')
        if folder().exists():shutil.rmtree(folder())
        shutil.move(str(target),str(folder()))
def command():
    if not available():raise ValueError('Install LC0 from Engine library first.')
    return [str(executable()),'--weights='+str(folder()/NETWORK),'--backend=blas','--minibatch-size=1','--nncache=20000']
