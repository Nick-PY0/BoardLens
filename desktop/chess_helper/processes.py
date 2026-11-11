"""Keep GUI-launched Windows helpers from creating console windows."""
import os,subprocess

def windowless_children():
    if os.name!='nt' or getattr(subprocess.Popen,'_boardlens_windowless',False):return
    original=subprocess.Popen
    class WindowlessPopen(original):
        _boardlens_windowless=True
        def __init__(self,*args,**kwargs):
            flags=kwargs.get('creationflags',0)
            if not flags&subprocess.CREATE_NEW_CONSOLE:kwargs['creationflags']=flags|subprocess.CREATE_NO_WINDOW
            super().__init__(*args,**kwargs)
    subprocess.Popen=WindowlessPopen
