"""Create optional Python runtimes without breaking relocatable macOS builds."""
from pathlib import Path
import os,sys,venv

def create_runtime(root):
    root=Path(root)
    # CPython's relocatable macOS binary resolves libpython beside its real
    # executable. Copying it into a venv loses that library; symlinks preserve
    # the original executable location. Repair only managed Python launchers.
    config=root/'pyvenv.cfg'
    if os.name!='nt' and config.is_file() and '--copies' in config.read_text():
        for name in ('python','python3',f'python{sys.version_info.major}.{sys.version_info.minor}'):
            target=root/'bin'/name
            if target.exists() or target.is_symlink():target.unlink()
    venv.EnvBuilder(with_pip=True,symlinks=os.name!='nt').create(root)
