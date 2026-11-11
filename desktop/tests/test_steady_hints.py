from copy import deepcopy
from chess_helper.hints import LiveHintFilter


def sample(move,reply='e7e5',fen='position',provisional=True):
    return {'fen':fen,'provisional':provisional,'lines':[{'move':move,'reply_move':reply,'cp':20}]}


def test_steady_hints_keep_first_immediate_and_wait_for_consistent_replacement():
    hints=LiveHintFilter(.25)
    assert hints.select(sample('e2e4'),True,now=0)['lines'][0]['move']=='e2e4'
    assert hints.select(sample('d2d4'),True,now=.1)['lines'][0]['move']=='e2e4'
    assert hints.select(sample('d2d4'),True,now=.2)['lines'][0]['move']=='e2e4'
    assert hints.select(sample('d2d4'),True,now=.36)['lines'][0]['move']=='d2d4'


def test_steady_hints_reject_flashing_replies_but_never_delay_final_or_new_position():
    hints=LiveHintFilter(.25);hints.select(sample('e2e4'),True,now=0)
    assert hints.select(sample('e2e4','c7c5'),True,now=.1)['lines'][0]['reply_move']=='e7e5'
    assert hints.select(sample('e2e4','e7e5'),True,now=.2)['lines'][0]['reply_move']=='e7e5'
    assert hints.select(sample('d2d4',provisional=False),True,now=.21)['lines'][0]['move']=='d2d4'
    assert hints.select(sample('g8f6',fen='new-position'),True,now=.22)['lines'][0]['move']=='g8f6'


def test_toggle_off_shows_live_result_and_filter_does_not_mutate_engine_evaluation():
    hints=LiveHintFilter();hints.select(sample('e2e4'),True,now=0)
    newer=sample('d2d4');newer['lines'][0]['cp']=99;before=deepcopy(newer)
    assert hints.select(newer,True,now=.1)['lines'][0]['move']=='e2e4'
    assert newer==before and newer['lines'][0]['cp']==99
    assert hints.select(newer,False,now=.2) is newer
