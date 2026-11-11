import json
import re
from pathlib import Path

import pytest
from PySide6.QtWidgets import QAbstractButton

from chess_helper.app import MainWindow
from chess_helper.core import data_dir, load_settings
from chess_helper.help_index import topics


def test_study_and_coaching_are_removed_without_deleting_existing_data(qt):
    root = data_dir()
    games = root / 'games'
    games.mkdir(parents=True)
    preserved = {games / 'existing.json': b'{"existing":"saved game"}',
                 root / 'guided-practice.json': b'{"completed":["knight"]}'}
    for path, contents in preserved.items():
        path.write_bytes(contents)
    (root / 'settings.json').write_text(json.dumps({
        'active_preset': 'coach', 'seconds': 0.7, 'depth': 19,
        'study_seconds': 2, 'sandbox_auto': True, 'auto_save_games': True,
    }))
    w = MainWindow()
    try:
        assert not hasattr(w, 'study') and not hasattr(w, 'open_study')
        assert not hasattr(w, 'auto_save_games')
        assert w.seconds.value() == .7 and w.depth.value() == 19
        assert w.preset_combo.currentData() is None
        assert not any(re.search(r'study|coaching|lessons|puzzles|what-if|saved games',
                                 button.text(), re.I)
                       for button in w.findChildren(QAbstractButton))
        state = w.phone.snapshot()
        assert 'study' not in state and 'auto_save_games' not in state['settings']
        assert {p['id'] for p in state['presets']} == {'quick', 'deep'}
        assert not re.search(r'study|coaching|guided|what-if', json.dumps(topics()), re.I)
    finally:
        w.close()
    assert all(path.read_bytes() == contents for path, contents in preserved.items())
    assert not {'study_seconds', 'sandbox_auto', 'auto_save_games'} & load_settings().keys()


@pytest.mark.parametrize('command', [
    'save_game', 'select_game', 'game_position', 'rename_game', 'import_pgn',
    'review_game', 'cancel_review', 'whatif_rebase', 'whatif_move',
    'whatif_click', 'whatif_undo', 'whatif_reset', 'whatif_analyze',
    'whatif_stop', 'study_limits', 'study_preferences', 'lesson_select',
    'lesson_click', 'lesson_move', 'lesson_hint', 'lesson_show',
    'lesson_retry', 'lesson_next', 'lesson_whatif',
])
def test_removed_remote_commands_are_rejected(qt, command):
    w = MainWindow()
    try:
        with pytest.raises(ValueError, match='Unknown companion command'):
            w.phone.execute({'command': command})
    finally:
        w.close()


def test_phone_presets_work_without_study_over_authenticated_http(qt):
    from test_phone import request, through_qt
    w = MainWindow()
    w.phone.start(0, host='127.0.0.1')
    server = w.phone.server
    try:
        token = request(server, '/api/pair', {'code': server.code})[1]['token']
        def send(name, data=None):
            return through_qt(qt, lambda: request(server, '/api/command',
                              {'command': name, 'data': data or {}}, token))
        assert send('apply_preset', {'id': 'quick'})[0] == 200
        assert w.seconds.value() == .3
        assert send('save_preset', {'name': 'Phone analysis'})[0] == 200
        state = request(server, '/api/state', token=token)[1]
        saved = next(p for p in state['presets'] if p['name'] == 'Phone analysis')
        assert 'study' not in state
        assert send('delete_preset', {'id': saved['id']})[0] == 200
        assert send('save_game')[0] == 400
    finally:
        w.close()


def test_phone_has_four_tabs_and_no_study_controls():
    root = Path(__file__).parents[1]
    phone = root / 'chess_helper/assets/phone'
    html = (phone / 'index.html').read_text()
    script = (phone / 'app.js').read_text()
    assert re.findall(r'data-page="([^"]+)"', html) == ['boards', 'analysis', 'settings', 'controls']
    assert not re.search(r'study|guided|lesson_|whatif_|save_game', html + script, re.I)
    assert 'analysis-preset' in html and 'state.presets' in script
