import chess
import pytest
from PySide6.QtCore import Qt

from chess_helper.app import MainWindow
from chess_helper.core import find_engine
from chess_helper.practice import choose_practice_line


@pytest.mark.parametrize("black",[False,True])
def test_practice_loss_limit_for_both_colors(black):
    board=chess.Board()
    if black:
        board.push_uci("e2e4")
    lines=[{"move":move,"cp":cp,"mate":None} for move,cp in
           ([("e7e5",-50),("c7c5",-30),("a7a5",120)] if black else
            [("e2e4",50),("d2d4",30),("a2a4",-120)])]
    choice=choose_practice_line(board,lines,chance=1,max_loss_cp=40,random_value=0)
    assert choice is lines[1]
    assert choose_practice_line(board,lines,chance=1,max_loss_cp=10,random_value=0) is lines[0]
    assert choose_practice_line(board,lines,chance=0,max_loss_cp=40,random_value=.2) is lines[0]
    lines[0]["mate"]=3
    assert choose_practice_line(board,lines,chance=1,max_loss_cp=1000,random_value=0) is lines[0]


def test_practice_rejects_queen_giveaway_even_if_shallow_score_is_close():
    board=chess.Board("4k3/8/8/8/8/4p3/8/3QK3 w - - 0 1")
    lines=[{"move":"d1a4","cp":800,"mate":None},{"move":"d1d2","cp":790,"mate":None}]
    assert chess.Move.from_uci("d1d2") in board.legal_moves
    assert choose_practice_line(board,lines,chance=1,max_loss_cp=40,random_value=0) is lines[0]


def test_display_toggles_and_click_through_overlay(qt):
    window=MainWindow()
    board=window.tracker.board
    window.result={"fen":board.fen(),"lines":[
        {"move":"e2e4","reply_move":"e7e5","cp":20,"mate":None},
        {"move":"d2d4","cp":18,"mate":None},
        {"move":"g1f3","cp":15,"mate":None}]}
    window.update_visuals()
    assert len(window.board_view.arrows)==3
    window.show_white.blockSignals(True)
    window.show_white.setChecked(False)
    window.show_white.blockSignals(False)
    window.update_visuals()
    assert len(window.board_view.arrows)==1 and window.board_view.arrows[0]["reply"]
    assert window.overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput
    assert window.overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    window.stop()
    assert not window.overlay.isVisible()
    window.result=None
    window.close()


def test_knight_arrow_follows_an_l_shape(qt):
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QImage,QPainter
    from chess_helper.overlay import paint_arrows
    image=QImage(640,640,QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image)
    paint_arrows(painter,QRectF(0,0,640,640),True,[{"move":chess.Move.from_uci("b1c3"),"color":"#ffc65c"}])
    painter.end()
    assert image.pixelColor(120,520).alpha()>0
    assert image.pixelColor(160,520).alpha()==0
    assert image.pixelColor(200,440).alpha()>0
