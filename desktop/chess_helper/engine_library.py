"""Optional, explicitly installed engines and published Tiny Chess Bot entries."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,sys,tarfile,tempfile,urllib.request,venv,zipfile
from .runtime_setup import create_runtime
from .core import data_dir,find_engine

BOT_COMMIT='fcebda936c5882efdeb61382592bda77f2c1e6c0'
MAIA2_COMMIT='67bee6ce7e2f264344fe6d2026a2e18c76a82efa'
@dataclass(frozen=True)
class Entry:
    identity:str
    label:str
    kind:str
    size:str
    rating:int|None=None
    heavy:bool=False
    bot:int|None=None
    model:str=''
    difficulty:str=''

ENTRIES=[
 Entry('stockfish','Stockfish','stockfish','Official UCI engine'),
 Entry('maia3','Maia-3 · 5M human model','maia3','About 25 MB model + large PyTorch runtime',heavy=True,model='maia3-5m'),
 Entry('custom','Custom UCI','custom','Choose an existing executable'),
 Entry('maia2','Maia-2 · Rapid human model','maia2','Large model + separate PyTorch runtime',heavy=True),
 Entry('flounder','Flounder · Stockfish-based','flounder','Uses installed Stockfish',rating=1500),
 Entry('tiny17','The CopyCat','tiny','Small bot source + shared .NET runtime',192,bot=17,difficulty='Absolute beginner'),
 Entry('tiny278','Bongcloud Enthusiast','tiny','Small bot source + shared .NET runtime',307,bot=278,difficulty='Easy'),
 Entry('tiny153','WhateverBot','tiny','Small bot source + shared .NET runtime',677,bot=153,difficulty='Casual'),
 Entry('tiny70','applemethod-orz','tiny','Small bot source + shared .NET runtime',1085,bot=70,difficulty='Intermediate'),
 Entry('tiny253','Squeedo','tiny','Small bot source + shared .NET runtime',1276,bot=253,difficulty='Challenging'),
 Entry('tiny425','200 Tokens Monstrosity','tiny','Small bot source + shared .NET runtime',1569,bot=425,difficulty='Advanced'),
 Entry('tiny266','Game Tech Explained','tiny','Small bot source + shared .NET runtime',1713,bot=266,difficulty='Expert'),
 Entry('tiny303','Electric Shockwave Gambit','tiny','Small bot source + shared .NET runtime',2001,bot=303,difficulty='Master'),
 Entry('tiny628','King Gambot IV','tiny','Small bot source + shared .NET runtime',2172,bot=628,difficulty='Strong master'),
 Entry('tiny529','NNBot','tiny','Small bot source + shared .NET runtime',2246,bot=529,difficulty='Elite'),
 Entry('tiny610','TinyHugeBot','tiny','Small bot source + shared .NET runtime',2513,bot=610,difficulty='Grandmaster'),
 Entry('tiny614','Boychesser','tiny','Small bot source + shared .NET runtime',2772,bot=614,difficulty='Top tournament bot'),
 Entry('maia3-23m','Maia-3 · 23M model','maia3','About 95 MB model + shared Maia-3 runtime',heavy=True,model='maia3-23m'),
 Entry('maia3-79m','Maia-3 · 79M model','maia3','About 320 MB model + shared Maia-3 runtime',heavy=True,model='maia3-79m'),
 Entry('lc0','LC0 · Leela Chess Zero','lc0','Optional CPU engine + 19 MB network'),
]
BY_ID={e.identity:e for e in ENTRIES}
BOT_HASHES={'17': '4b5aeb1a89b18e6c3bb2e9a3f993dd4be1b00b7113ad9012e7a84fb0a182acbc', '278': '3dc71df38ca3b076239f629e632f53f8883f8bc3dbd55fea17b79b1042cd7bfe', '153': 'f8af17ac167b43c5b7b72d26371bd11b013a3fe4123302be9ea99da7e25c4d0b', '70': 'd027e9e0fd000759f1b6d5dcb1a2c145a8889cba15f5a507b1bc783e61e5116f', '253': '1d964843ac03bdf93b950112475dd387bb2c16b21d49ff31cf3abdd331bcecf4', '425': 'f09b0152d6c7c8ff3f834c3936cae3e98d3c6a0106bcbb71d8b76fa49905c0da', '266': 'bf47651a80ba9b962b9290075e3584c0a13c605b83418251e255dfde74558d48', '303': '0e89f85049cde1288fe554707495113abeb80722aa5ec53bf2daf15af7f5093e', '628': 'ea027f0e874f1f63b8107cf5805f2e13eae280a1101c61d333095764ad66f947', '529': 'ad7cac0623707e721502159cc16549b518a48592da7952a94c4b44c284160280', '610': 'b207c388e07c9d052e74f66c1809c4950bc20555177168cf5c65e7cb783fc60a', '614': '8961dd5fe26591a265a9978ea500c9fce2eac9292ce886c77cb58119b5633c21'}

def selected(index):return ENTRIES[index]
def python_path(root):return root/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
def runtime_path():return data_dir()/'tiny-runtime'/('dotnet.exe' if os.name=='nt' else 'dotnet')
def bot_path(entry):return data_dir()/'tiny-bots'/f'Bot_{entry.bot}.cs'
def marker(entry):return data_dir()/'engine-library'/(entry.identity+'.json')

def available(entry):
    if entry.kind=='stockfish':return bool(find_engine())
    if entry.kind=='flounder':return bool(find_engine())
    if entry.kind=='custom':return True
    if entry.kind=='lc0':
        from .lc0_support import available as lc0_available
        return lc0_available()
    if entry.kind=='tiny':return runtime_path().is_file() and bot_path(entry).is_file()
    if entry.kind=='maia3':
        size=entry.model.rsplit('-',1)[-1].upper()
        cached=any((data_dir()/'maia3-cache').glob(f'hub/models--UofTCSSLab--Maia3-{size}/snapshots/*/{entry.model}.pt'))
        return python_path(data_dir()/'maia3-runtime').is_file() and cached
    if entry.kind=='maia2':return marker(entry).is_file() and python_path(data_dir()/'maia2-runtime').is_file() and (data_dir()/'maia2-models/rapid_model.pt').is_file()
    return marker(entry).is_file()

def fetch(url,target,algorithm=None,expected=None):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    descriptor,temporary=tempfile.mkstemp(prefix='boardlens-download-',dir=target.parent);os.close(descriptor);temporary=Path(temporary)
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BoardLens/2.7'}),timeout=90) as source,temporary.open('wb') as output:shutil.copyfileobj(source,output)
        if expected and hashlib.new(algorithm,temporary.read_bytes()).hexdigest().lower()!=expected.lower():raise ValueError('Download checksum mismatch; installation was not completed.')
        temporary.replace(target)
    finally:temporary.unlink(missing_ok=True)


def ensure_tiny_runtime():
    dest=data_dir()/'tiny-runtime'
    if runtime_path().is_file():return
    arch='arm64' if platform.machine().lower() in ('arm64','aarch64') else 'x64'
    system={'Darwin':'osx','Windows':'win','Linux':'linux'}.get(platform.system())
    if system is None:raise ValueError('Tiny bots are not available for this operating system.')
    rid=system+'-'+arch
    with urllib.request.urlopen('https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json',timeout=30) as response:releases=json.load(response)
    runtime=next(r['runtime'] for r in releases['releases'] if r.get('runtime') and r['runtime']['version']==releases['latest-runtime'])
    asset=next(f for f in runtime['files'] if f['rid']==rid and f['name'].startswith('dotnet-runtime-') and f['name'].endswith('.zip' if os.name=='nt' else '.tar.gz'))
    with tempfile.TemporaryDirectory(prefix='boardlens-dotnet-',dir=data_dir()) as folder:
        staged=Path(folder)/'runtime';staged.mkdir()
        archive=Path(folder)/asset['name'];fetch(asset['url'],archive,'sha512',asset['hash'])
        if os.name=='nt':
            with zipfile.ZipFile(archive) as z:
                for item in z.infolist():
                    if item.filename.startswith('/') or '..' in Path(item.filename).parts:raise ValueError('Invalid runtime archive.')
                z.extractall(staged)
        else:
            with tarfile.open(archive) as t:t.extractall(staged,filter='data')
        if not (staged/('dotnet.exe' if os.name=='nt' else 'dotnet')).is_file():raise ValueError('The downloaded runtime has no executable.')
        if dest.exists():shutil.rmtree(dest)
        shutil.move(str(staged),str(dest))
    if os.name!='nt':runtime_path().chmod(0o755)

def install(identity):
    entry=BY_ID[identity]
    required=3_000_000_000 if entry.heavy or entry.kind=='maia3' else 200_000_000 if entry.kind=='tiny' else 50_000_000
    if shutil.disk_usage(data_dir()).free<required:raise ValueError(f'Free at least {required//1_000_000} MB before installing this engine.')
    if entry.kind in ('stockfish','flounder'):
        if not find_engine():
            from .installer import install_stockfish
            install_stockfish(data_dir()/'engine')
    elif entry.kind=='lc0':
        from .lc0_support import install as install_lc0
        install_lc0()
    elif entry.kind=='custom':raise ValueError('Custom UCI uses an executable you choose; no download is needed.')
    elif entry.kind=='tiny':
        ensure_tiny_runtime()
        fetch(f'https://raw.githubusercontent.com/SebLague/Tiny-Chess-Bot-Challenge-Results/{BOT_COMMIT}/Bots/Bot_{entry.bot}.cs',bot_path(entry),'sha256',BOT_HASHES[str(entry.bot)])
    elif entry.kind=='maia2':
        root=data_dir()/'maia2-runtime';create_runtime(root);python=python_path(root)
        log=data_dir()/'maia2-install.log'
        with log.open('w') as output:
            if os.name=='nt':subprocess.run([str(python),'-m','pip','install','torch>=2.8,<2.9','--index-url','https://download.pytorch.org/whl/cpu'],stdout=output,stderr=subprocess.STDOUT,check=True,timeout=1200)
            subprocess.run([str(python),'-m','pip','install',f'https://github.com/CSSLab/maia2/archive/{MAIA2_COMMIT}.zip'],stdout=output,stderr=subprocess.STDOUT,check=True,timeout=1200)
            subprocess.run([str(python),str(Path(__file__).with_name('maia2_uci.py')),'--cache','--model-dir',str(data_dir()/'maia2-models')],stdout=output,stderr=subprocess.STDOUT,check=True,timeout=600)
    elif entry.kind=='maia3':
        from .engine_config import install_maia3,maia_python
        if not maia_python().is_file():install_maia3()
        with (data_dir()/'maia3-install.log').open('a') as output:
            subprocess.run([str(maia_python()),'-m','maia3.cache','--model',entry.model],env=dict(os.environ,HF_HOME=str(data_dir()/'maia3-cache')),stdout=output,stderr=subprocess.STDOUT,check=True,timeout=900)
    target=marker(entry);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps({'engine':identity,'source':BOT_COMMIT if entry.kind=='tiny' else MAIA2_COMMIT if entry.kind=='maia2' else 'official'}))

def extra_command(entry):
    if not available(entry):raise ValueError('This engine is not installed. Open Engine library and download it first.')
    if entry.kind=='lc0':
        from .lc0_support import command
        return command()
    if entry.kind=='tiny':return [str(runtime_path()),str(Path(__file__).parent/'assets/tiny/BoardLensTiny.dll'),str(bot_path(entry)),entry.label]
    if entry.kind=='maia2':return [str(python_path(data_dir()/'maia2-runtime')),str(Path(__file__).with_name('maia2_uci.py')),'--model-dir',str(data_dir()/'maia2-models')]
    if entry.kind=='maia3':
        from .engine_config import maia_command
        args=maia_command();args[args.index('--model')+1]=entry.model;return args
    raise ValueError('Engine command is supplied by the desktop settings.')
