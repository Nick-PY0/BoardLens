"""Opt-in packaged-app verification, isolated by the launcher's self-test mode."""
import json,os,sys,time
from pathlib import Path
import chess,cv2
from PySide6.QtCore import QTimer

def begin(app,window,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);started=time.monotonic();report={'version':__import__('chess_helper').__version__,'python':sys.executable,'application':app.applicationName(),'icon_loaded':not app.windowIcon().isNull(),'tty':bool(sys.stdout and sys.stdout.isatty()),'runtime_in_bundle':bool(os.environ.get('BOARDLENS_BUNDLED_RUNTIME'))}
    if sys.platform=='darwin':
        from Foundation import NSBundle
        import Quartz
        report['mac_bundle']=NSBundle.mainBundle().bundleIdentifier()
        report['mac_host']=NSBundle.mainBundle().executablePath()
        report['screen_access']=bool(Quartz.CGPreflightScreenCaptureAccess())
    if os.name=='nt':
        import ctypes
        report['console_window']=int(ctypes.windll.kernel32.GetConsoleWindow() or 0)
    try:
        from .recognition import Recognizer,position_from_read
        fixture=Path(__file__).parent.parent/'tests/fixtures/chesscom-italian-white.png';read=Recognizer().scan(cv2.imread(str(fixture)))
        assert read is not None,'Bundled board model did not recognize the fixture'
        report['recognized_fen']=position_from_read(read)[0].board_fen()
        window.source.setCurrentIndex(0);window.seconds.setValue(.15);window.threads.setValue(1);window.new_game();window.suggest()
    except Exception as error:report['error']=str(error)
    timer=QTimer(window)
    def finish():
        ready=window.result and window.job is None
        if not report.get('error') and not ready and time.monotonic()-started<60:return
        if ready:
            result=window.result;move=chess.Move.from_uci(result['lines'][0]['move']);report.update(move=move.uci(),legal_move=move in window.tracker.board.legal_moves,engine=result['engine'])
        elif not report.get('error'):report['error']='Engine self-test timed out: '+window.status_label.text()
        report['elapsed']=round(time.monotonic()-started,3);temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2));temporary.replace(path);timer.stop();window.close();app.exit(1 if report.get('error') else 0)
    timer.timeout.connect(finish);timer.start(100);finish()
