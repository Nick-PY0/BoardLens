import json
from pathlib import Path
import chess
import pytest
from PySide6.QtCore import QPoint,Qt
from chess_helper.help_index import HelpIndex,topics
from chess_helper.app import MainWindow


@pytest.mark.parametrize('query,expected',[
 ('why do my arrows keep changing','arrow-steady'),
 ('it forgets my options when I quit','preferences'),
 ('can I use 3d without the extension','connections'),
 ('the arrows are taking ages','speed'),
 ('my phone changes do not reach the laptop','phone-sync'),
 ('Maya depth disabled','maia'),
 ('engien thinkng tim','limits'),
 ('did it copy the pairing key','copy'),
 ('my turquoise line is dashed','arrows'),
 ('why does the bar always say white wins','eval'),
 ('I switched apps and still see the old position','target'),
])
def test_help_answers_questions_and_paraphrases(query,expected):
    assert expected in [item['id'] for item in HelpIndex().search(query)[:3]]


def test_help_covers_every_exposed_setting_and_handles_unknown_questions():
    from chess_helper.phone import NUMBERS,BOOLEANS,ENUMS
    guides=topics();covered={key for item in guides for key in item['controls']}
    assert set(NUMBERS)|set(BOOLEANS)|set(ENUMS)<=covered
    assert len({item['category'] for item in guides})>=7
    assert all(item['steps'] and item['details'] and item['questions'] for item in guides)
    index=HelpIndex();assert index.search('zzzxxyy123')==[]
    assert all(t['category']=='Phone and tablet' for t in index.search('connect','Phone and tablet'))












def test_sidebar_cannot_pan_after_expansion_resize_and_horizontal_scroll(qt):
    w=MainWindow();w.show();w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False);w.source_controls();w.readers_toggle.setChecked(True)
    try:
        for width,height in [(1400,900),(1180,740),(1600,960)]:
            w.resize(width,height)
            for tab in range(5):
                w.settings_tabs.setCurrentIndex(tab)
                for _ in range(3):qt.processEvents()
                area=w.settings_tabs.widget(tab);area.fit();qt.processEvents()
                assert area.widget().width()==area.viewport().width()
                area.horizontalScrollBar().setValue(100);assert area.widget().x()==0 and area.horizontalScrollBar().maximum()==0
        w.toggle_compact(True);w.open_settings();w.settings_dialog.resize(420,650);qt.processEvents()
        for tab in range(5):
            w.settings_tabs.setCurrentIndex(tab);qt.processEvents();area=w.settings_tabs.widget(tab);area.fit()
            assert area.widget().width()==area.viewport().width() and area.horizontalScrollBar().maximum()==0
    finally:w.close()


def test_help_navigation_live_search_empty_fallback_and_all_topics(qt):
    w=MainWindow()
    try:
        w.help();dialog=w.help_dialog;dialog.search.setText('it forgets my options when I quit');dialog.refresh();qt.processEvents()
        assert 'Settings save automatically' in dialog.browser.toPlainText()
        assert dialog.list.item(0).text()=='Settings save automatically'
        dialog.category.setCurrentText('Practice and history');dialog.search.setText('load an exact position');dialog.refresh()
        assert 'Load and copy a FEN position' in dialog.browser.toPlainText()
        dialog.search.setText('zzzxxyy123');dialog.refresh();assert 'Try another question' in dialog.browser.toPlainText()
        dialog.clear_filters();assert dialog.list.count()==len(topics())
        dialog.resize(700,560);qt.processEvents();assert dialog.browser.horizontalScrollBar().maximum()==0
    finally:w.close()
