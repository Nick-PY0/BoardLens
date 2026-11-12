"""Explicit engine profiles and an optional isolated Maia-3 runtime."""
from __future__ import annotations
import json,os,subprocess,sys,venv
from dataclasses import asdict,replace
from pathlib import Path
from .runtime_setup import create_runtime
from .core import data_dir
from . import engine_library

MAIA_COMMIT='1e13597c42d4858b7cfd7cfdae01e297263364b2'
ENGINE_NAMES=[entry.label for entry in engine_library.ENTRIES]
COMPARE_NAMES=['Stockfish · maximum','Stockfish · selected strength','Maia-3 · selected rating','Custom UCI']+[entry.label for entry in engine_library.ENTRIES[3:]]

def entry(window):return engine_library.selected(window.engine_kind.currentIndex())
def is_human(window):return entry(window).kind in ('maia3','maia2')
def is_tiny(window):return entry(window).kind=='tiny'

def maia_python():
    return data_dir()/'maia3-runtime'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')

def maia_command():
    path=maia_python()
    if not engine_library.available(engine_library.ENTRIES[1]):raise ValueError('Maia-3 is not installed. Open Engine library to download it.')
    return [str(path),'-m','maia3.uci','--model','maia3-5m','--device','cpu','--no-use-amp','--temperature','0','--use-uci-history']

def command(window,kind=None):
    index=window.engine_kind.currentIndex() if kind is None else kind
    selected=engine_library.selected(index)
    if index==1:return maia_command()
    if index>2 and selected.kind!='flounder':return engine_library.extra_command(selected)
    path=window.custom_engine.text().strip() if selected.kind=='custom' else window.engine_path.text().strip()
    if not path or not Path(path).is_file():raise ValueError('Choose the executable for the selected engine in the Engine tab.')
    return path

def profile(window,index):
    settings=replace(window.search_settings(),multipv=window.multipv.value())
    if index==0:return command(window,0),replace(settings,engine_kind='stockfish',engine_id='stockfish',strength='Full strength',style='Balanced')
    if index==1:return command(window,0),replace(settings,engine_kind='stockfish',engine_id='stockfish',strength=window.strength_mode.currentText())
    if index==2:return command(window,1),replace(settings,engine_kind='maia3',engine_id='maia3',strength='Full strength')
    selected=engine_library.ENTRIES[2 if index==3 else index-1]
    return command(window,engine_library.ENTRIES.index(selected)),replace(settings,engine_kind=selected.identity if selected.kind=='tiny' else selected.kind,engine_id=selected.identity,strength='Full strength',multipv=1 if selected.kind=='tiny' else settings.multipv)

def summary(window):
    settings=window.search_settings();kind=window.engine_kind.currentIndex()
    strength=f'human rating {settings.human_elo}' if is_human(window) else f'Skill {settings.skill}/20' if settings.strength=='Skill level' else f'Elo {settings.elo}' if settings.strength=='Elo rating' else 'maximum strength'
    limit=f'one model pass · prediction {settings.prediction_plies} plies / {settings.prediction_seconds:g}s reply budget' if is_human(window) else f'{settings.seconds:g}s' if settings.mode=='Time' else f'depth {settings.depth}' if settings.mode=='Depth' else f'{settings.seconds:g}s / depth {settings.depth}'
    strength=f'reference Elo {entry(window).rating}' if is_tiny(window) else f'target {settings.human_elo}' if entry(window).kind=='flounder' else strength
    return f'{ENGINE_NAMES[kind]} · {strength}\n{limit} · {window.multipv.value()} recommended moves\nStyle: {settings.style}'

def configuration(window):
    values=asdict(window.search_settings());values['engine']=ENGINE_NAMES[window.engine_kind.currentIndex()]
    _,evaluator,limits=window.evaluations.profile()
    values['evaluation']={'engine':evaluator.identity,'settings':asdict(limits)}
    values['stockfish_path']=window.engine_path.text();values['custom_path']=window.custom_engine.text()
    return json.dumps(values,indent=2)

def install_maia3():
    runtime=data_dir()/'maia3-runtime';python=maia_python()
    create_runtime(runtime)
    log=data_dir()/'maia3-install.log'
    env=dict(os.environ,HF_HOME=str(data_dir()/'maia3-cache'),PIP_DISABLE_PIP_VERSION_CHECK='1')
    with log.open('w') as output:
        if os.name=='nt':
            subprocess.run([str(python),'-m','pip','install','torch','--index-url','https://download.pytorch.org/whl/cpu'],stdout=output,stderr=subprocess.STDOUT,env=env,check=True,timeout=900)
        subprocess.run([str(python),'-m','pip','install',f'https://github.com/CSSLab/maia3/archive/{MAIA_COMMIT}.zip'],stdout=output,stderr=subprocess.STDOUT,env=env,check=True,timeout=900)
        subprocess.run([str(python),'-m','maia3.cache','--model','maia3-5m'],stdout=output,stderr=subprocess.STDOUT,env=env,check=True,timeout=600)
    return str(python)
