"""Run a private, bundled Python runtime; the user's GUI settings live separately."""
import importlib.util,json,os,re,sys,time
from pathlib import Path

package=Path(__file__).resolve().parent
if sys.platform=='win32':
    import subprocess
    original=subprocess.Popen
    class QuietPopen(original):
        def __init__(self,*args,**kwargs):
            kwargs['creationflags']=kwargs.get('creationflags',0)|subprocess.CREATE_NO_WINDOW
            super().__init__(*args,**kwargs)
    subprocess.Popen=QuietPopen
root=Path(os.environ['BOARDLENS_NATIVE_DATA']);app=root/'application';metadata=json.loads((package/'metadata.json').read_text())
def version(path):
    try:return tuple(map(int,re.search(r'__version__\s*=\s*"([0-9.]+)"',path.read_text()).group(1).split('.')))
    except (OSError,AttributeError,ValueError):return (0,0,0)
if version(app/'chess_helper/__init__.py')<tuple(map(int,metadata['version'].split('.'))):
    spec=importlib.util.spec_from_file_location('boardlens_install',package/'update_apply.py');installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
    installer.apply_archive(package/'source.zip',app,root/'backups'/str(time.time_ns()))
python=package/'runtime'/('pythonw.exe' if os.name=='nt' else 'bin/python3')
engine=next((p for p in (package/'engine').iterdir() if p.is_file() and p.name.startswith('stockfish')),None)
if engine:os.environ.setdefault('STOCKFISH_EXECUTABLE',str(engine))
os.environ.update(BOARDLENS_NATIVE_PYTHON=str(python),PYTHONNOUSERSITE='1',PYTHONUNBUFFERED='1')
os.chdir(app)
os.execv(str(python),[str(python),str(app/'launch.py')])
