import json,time,subprocess,sys,venv,os
from chess_helper.app import MainWindow
from chess_helper.core import data_dir
from chess_helper.runtime_setup import create_runtime


def test_valid_settings_autosave_without_pressing_save(qt):
    w=MainWindow();w.seconds.setValue(2.4);w.playing_style.setCurrentText('Defensive');w.arrow_count.setValue(3)
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        qt.processEvents();time.sleep(.01)
        path=data_dir()/'settings.json'
        if path.exists() and json.loads(path.read_text()).get('seconds')==2.4:break
    values=json.loads(path.read_text());assert values['seconds']==2.4 and values['playing_style']==2 and values['arrow_count']==3
    w.close();restored=MainWindow()
    try:assert restored.seconds.value()==2.4 and restored.playing_style.currentText()=='Defensive' and restored.arrow_count.value()==3
    finally:restored.close()


def test_optional_runtime_repairs_copied_python_and_boots_with_pip(tmp_path):
    root=tmp_path/'optional-runtime'
    venv.EnvBuilder(with_pip=False,symlinks=False).create(root)
    create_runtime(root)
    python=root/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if os.name!='nt':assert python.is_symlink()
    result=subprocess.run([str(python),'-m','pip','--version'],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
