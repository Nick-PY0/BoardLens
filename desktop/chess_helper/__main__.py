import os
import sys


def main():
    from .processes import windowless_children
    windowless_children()
    # Some macOS download/cache tools propagate Finder's hidden flag to every
    # plugin. Qt intentionally skips hidden plugins, even at an explicit path.
    if sys.platform == "darwin":
        import stat
        from pathlib import Path
        import PySide6
        plugins = Path(PySide6.__file__).parent / "Qt" / "plugins"
        for item in [plugins, *plugins.rglob("*")]:
            try:
                flags = item.stat().st_flags
                if flags & stat.UF_HIDDEN:
                    os.chflags(item, flags & ~stat.UF_HIDDEN)
            except OSError:
                pass
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            pass
    from .updater import apply_pending_on_launch,AutomaticUpdates
    if apply_pending_on_launch():return
    from PySide6.QtWidgets import QApplication
    from .app import MainWindow
    app = QApplication(sys.argv)
    app.setApplicationName("BoardLens")
    app.setApplicationDisplayName("BoardLens")
    if sys.platform=="darwin" and os.environ.get("BOARDLENS_NATIVE_PYTHON"):
        from Foundation import NSProcessInfo
        NSProcessInfo.processInfo().setProcessName_("BoardLens")
    app.setOrganizationName("BoardLens")
    from .branding import app_icon
    app.setWindowIcon(app_icon())
    server=None
    if not os.environ.get('BOARDLENS_TEST_MODE'):
        from .instance import claim
        server=claim(app)
        if server is None:return
    window = MainWindow()
    if server:
        from .instance import attach
        attach(server,window)
    window.show()
    smoke=os.environ.get('BOARDLENS_NATIVE_SMOKE')
    if smoke:
        from .native_smoke import begin
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100,lambda:begin(app,window,smoke))
    else:window.automatic_updates=AutomaticUpdates(window)
    import signal
    signal.signal(signal.SIGTERM,lambda *_:(window.close(),app.quit()))
    diagnostics=os.environ.get('BOARDLENS_DIAGNOSTICS_PATH')
    if diagnostics:
        import json
        from pathlib import Path
        from PySide6.QtCore import QTimer
        def snapshot():
            panel=window.overlay._native_panel
            value={'version':__import__('chess_helper').__version__,'route':window._scan_route,'status':window.status_label.text(),
                   'fen':window.tracker.board.fen(),'white_bottom':window.white_bottom,'confirmed':window._screen_confirmed,
                   'native_status':window.native_reader.status,'arrows':[a['move'].uci() for a in window.board_view.arrows],
                   'overlay_visible':window.overlay.isVisible(),'overlay':panel.diagnostics() if panel else None,
                   'settings':{'seconds':window.seconds.value(),'multipv':window.multipv.value()},
                   'source':getattr(window._last_read,'source_id',None)}
            path=Path(diagnostics);temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value));temporary.replace(path)
        diagnostic_timer=QTimer(window);diagnostic_timer.timeout.connect(snapshot);diagnostic_timer.start(150)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
