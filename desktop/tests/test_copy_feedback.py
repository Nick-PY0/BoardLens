from chess_helper.app import MainWindow
from PySide6.QtWidgets import QApplication


def test_copy_actions_show_feedback_and_do_not_claim_empty_data_was_copied(qt):
    w=MainWindow();w.show()
    previous=QApplication.clipboard().text()
    try:
        w.copy_fen();qt.processEvents()
        assert QApplication.clipboard().text()==w.tracker.board.fen()
        assert w.copy_notice.isVisible() and w.copy_notice.text()=='Copied to clipboard.'
        assert w.copy_text('') is False and w.copy_notice.text()=='Nothing to copy yet.'
        assert QApplication.clipboard().text()==w.tracker.board.fen()
    finally:QApplication.clipboard().setText(previous);w.close()
