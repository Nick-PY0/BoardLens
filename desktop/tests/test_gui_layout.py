from pathlib import Path
from types import SimpleNamespace
import chess,chess.engine,cv2
from PySide6.QtCore import QPoint,QRect,QRectF
from PySide6.QtGui import QGuiApplication
from chess_helper.app import MainWindow
from chess_helper.engine import summarize
from chess_helper.recognition import Recognizer,position_from_read
from chess_helper.vision import Detection


def sample(board):
    return summarize(board,[{'pv':[chess.Move.from_uci(move)],'score':chess.engine.PovScore(chess.engine.Cp(cp),chess.WHITE),'depth':18}
                           for move,cp in [('e2e4',35),('d2d4',28),('g1f3',20)]],'Stockfish')


def test_exact_large_starting_layout_and_inaccurate_candidate_are_recognized():
    image=cv2.imread(str(Path(__file__).parent/'fixtures/chesscom-starting-layout-nov10.png'))
    recognizer=Recognizer();reads=recognizer.scan_all(image)
    assert len(reads)==1
    assert position_from_read(reads[0])[0].fen()==chess.STARTING_FEN
    refined=recognizer.read_candidate(image,Detection(372,441,1244,1.))
    assert refined.reliable and refined.detection.size>=1260
    assert position_from_read(refined)[0].fen()==chess.STARTING_FEN


def test_live_board_and_evaluation_are_large_aligned_and_do_not_overlap_controls(qt):
    w=MainWindow();w.toggle_compact(False);w.resize(1400,900);w.show()
    w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False)
    w._screen_confirmed=True;w.source_controls();w.refresh_board()
    w.result=sample(w.tracker.board);w.render_result(w.result);qt.processEvents()
    actual=w.board_view.board_rect()
    assert actual.width()>=420
    origin=w.board_view.mapTo(w.board_area,QPoint(round(actual.x()),round(actual.y())))
    assert abs(w.eval_bar.height()-actual.height())<=1
    assert abs(w.eval_bar.y()-origin.y())<=1
    assert w.eval_bar.width()>=60 and w.eval_bar.score_text()=='+0.35'
    assert w.eval_bar.score_label.font().pixelSize()>=14
    assert w.lines.viewport().height()>=480 and w.lines.viewport().width()>=300
    assert w.lines.horizontalScrollBar().maximum()==0
    board_origin=w.board_view.mapTo(w,QPoint(round(actual.x()),round(actual.y())))
    board_rect=QRectF(board_origin.x(),board_origin.y(),actual.width(),actual.height())
    for widget in (w.simple_label,w.previous_button,w.eval_label):
        pos=widget.mapTo(w,QPoint())
        assert not board_rect.intersects(QRectF(pos.x(),pos.y(),widget.width(),widget.height()))
    w.toggle_compact(True);w.resize(620,900);qt.processEvents()
    assert w.board_view.board_rect().width()>=350
    w.close()


def test_no_board_state_hides_fake_board_and_evaluation(qt):
    w=MainWindow();w.show()
    w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False)
    w.show_empty_board('No board detected yet');qt.processEvents()
    assert w.board_stack.currentIndex()==1
    assert w.board_view.isHidden() and w.eval_bar.isHidden()
    assert w.simple_label.isHidden() and w.fen_panel.isHidden()
    assert 'No board' in w.empty_title.text()
    assert 'Waiting for a board' in w.lines.toPlainText()
    w.close()


def test_full_analysis_wraps_independently_and_stays_open_during_scans(qt):
    w=MainWindow();w.resize(1400,900);w.show()
    w.rank_others.setChecked(True)
    w.result=sample(w.tracker.board);w.render_result(w.result)
    w.full_analysis_button.click();qt.processEvents()
    assert w.workspace_stack.currentIndex()==2
    assert w.sidebar_host.isHidden()
    assert w.full_analysis_browser.document()!=w.lines.document()
    assert w.full_analysis_browser.toPlainText()==w.lines.toPlainText()
    assert w.full_analysis_browser.viewport().width()>800
    assert w.full_analysis_browser.horizontalScrollBar().maximum()==0
    assert w.full_analysis_browser.verticalScrollBar().maximum()==0
    w.multi.layout_cards();qt.processEvents()
    assert w.workspace_stack.currentIndex()==2
    old=w.lines.document().defaultFont().pixelSize()
    w.resize_analysis_text(1)
    assert w.lines.document().defaultFont().pixelSize()==old+2
    assert w.full_analysis_browser.document().defaultFont().pixelSize()==old+2
    w.close()


def test_saved_expanded_window_at_compact_width_is_repaired(qt,monkeypatch):
    w=MainWindow()
    w.settings={'compact':False,'window_geometry':[-1597,-12,620,864],'seconds':4.5}
    screen=SimpleNamespace(availableGeometry=lambda:QRect(-2560,-98,2560,1055))
    monkeypatch.setattr(QGuiApplication,'screens',lambda:[screen])
    monkeypatch.delenv('BOARDLENS_TEST_MODE',raising=False)
    w.restore()
    assert w.width()>=1400 and w.height()>=740
    assert w.sidebar_host.isHidden() is False
    assert w.seconds.value()==4.5
    w.close()


def test_compact_expand_keeps_external_monitor_despite_stale_native_screen(qt,monkeypatch):
    w=MainWindow();w.resize(1400,900);w.move(-1597,-12);w.show();qt.processEvents()
    screens=[SimpleNamespace(availableGeometry=lambda:QRect(0,25,1512,920)),
             SimpleNamespace(availableGeometry=lambda:QRect(-2560,-98,2560,1055))]
    monkeypatch.setattr(QGuiApplication,'screens',lambda:screens)
    anchor=w.geometry().topLeft()
    for _ in range(3):
        w.user_toggle_compact(True);qt.processEvents()
        assert w.geometry().center().x()<0
        w.user_toggle_compact(False);qt.processEvents()
        assert w.geometry().center().x()<0
        assert screens[1].availableGeometry().contains(w.geometry())
        assert w.width()>=1400
    w.close()
