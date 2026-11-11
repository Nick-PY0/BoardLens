from __future__ import annotations

import threading
import time
import os
from copy import deepcopy
from dataclasses import replace

import chess
import chess.engine

from .recommendation_styles import flounder_index,style_index
from .core import SearchSettings, advantage, describe_move, move_insights, simple_move, data_dir


def engine_environment(path):
    env=dict(os.environ,HF_HOME=str(data_dir()/'maia3-cache'))
    if isinstance(path,list) and 'maia3.uci' in path:env['HF_HUB_OFFLINE']='1'
    if isinstance(path,list) and ('maia3.uci' in path or any('maia2_uci.py' in str(part) for part in path)):
        env.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1')
    return env


class EngineSession:
    """Keep Stockfish and its hash warm between positions; serialize searches."""
    def __init__(self):
        self.lock=threading.Lock()
        self.engine=None
        self.path=None

    def get(self,path):
        if self.engine is None or self.path!=path or self.engine.returncode.done():
            if self.engine:
                self.engine.close()
            self.engine=chess.engine.SimpleEngine.popen_uci(path,timeout=90 if isinstance(path,list) else 15,
                env=engine_environment(path))
            self.path=path
        return self.engine

    def close(self):
        if self.engine:
            self.engine.close()
            self.engine=None


class EngineJob:
    def __init__(self):
        self.cancelled = threading.Event()
        self.analysis = None
        self.lock = threading.Lock()
        self.session=None
        self.on_update=None

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            if self.analysis:
                self.analysis.stop()

    def run(self, path, board, settings: SearchSettings):
        if not board.is_valid():
            raise ValueError("Cannot analyze an invalid position.")
        if board.is_game_over():
            raise ValueError(f"Game over: {board.result()}")
        if self.session:
            while not self.session.lock.acquire(timeout=.03):
                if self.cancelled.is_set():return None
            try:
                if self.cancelled.is_set():return None
                return self._search(self.session.get(path),board,settings)
            except chess.engine.EngineTerminatedError:
                if self.cancelled.is_set():return None
                raise
            finally:
                self.session.lock.release()
        with chess.engine.SimpleEngine.popen_uci(path, timeout=90 if isinstance(path,list) else 15,
                env=engine_environment(path)) as engine:
            return self._search(engine,board,settings)

    def _search(self,engine,board,settings):
        pipeline_started=time.monotonic()
        result=self._search_once(engine,board,settings)
        if not result or self.cancelled.is_set() or not settings.predict_continuations:return result
        lead=result['lines'][0]
        if len(lead.get('pv_moves',[]))>=3:return result
        # One-move providers can still predict a continuation. Publish the
        # current move first; subsequent positions never replace its identity.
        if self.on_update:self.on_update(dict(deepcopy(result),continuation_pending=True))
        moves=list(lead.get('pv_moves') or [lead['move']]);probe=board.copy()
        for uci in moves:
            move=chess.Move.from_uci(uci)
            if move not in probe.legal_moves:return result
            probe.push(move)
        callback=self.on_update;self.on_update=None
        try:
            while len(moves)<3 and not probe.is_game_over() and not self.cancelled.is_set():
                next_result=self._search_once(engine,probe,replace(settings,multipv=1,predict_continuations=False))
                if not next_result:break
                move=chess.Move.from_uci(next_result['lines'][0]['move'])
                if move not in probe.legal_moves:break
                moves.append(move.uci());probe.push(move)
                if callback:
                    update=deepcopy(result);update['lines'][0].update(describe_continuation(board,moves));update['continuation_pending']=len(moves)<3;callback(update)
        finally:self.on_update=callback
        if self.cancelled.is_set():return None
        refreshed=describe_continuation(board,moves)
        result['lines'][0].update(refreshed);result['continuation_pending']=False;result['primary_elapsed']=result.get('elapsed',0);result['elapsed']=time.monotonic()-pipeline_started
        return result

    def _search_once(self,engine,board,settings):
        if self.cancelled.is_set():
            return None
        options = {}
        for name, value in (("Threads", settings.threads), ("Hash", settings.hash_mb), ("UCI_ShowWDL", True)):
            if name in engine.options:
                options[name] = value
        human=settings.engine_kind in ('maia3','maia2');tiny=settings.engine_kind.startswith('tiny');flounder=settings.engine_kind=='flounder'
        limited=not human and settings.strength!='Full strength'
        if 'Skill Level' in engine.options:options['Skill Level']=settings.skill if settings.strength=='Skill level' else engine.options['Skill Level'].max
        if 'UCI_LimitStrength' in engine.options:options['UCI_LimitStrength']=settings.strength=='Elo rating'
        if settings.strength=='Skill level' and not human and 'Skill Level' not in engine.options:
            raise ValueError('This engine does not support Skill Level. Choose full strength.')
        if settings.strength=='Elo rating' and not human:
            if 'UCI_Elo' not in engine.options or 'UCI_LimitStrength' not in engine.options:
                raise ValueError('This engine does not support Elo limiting. Choose full strength.')
            option=engine.options['UCI_Elo']
            if not option.min<=settings.elo<=option.max:raise ValueError(f'This engine supports Elo {option.min}–{option.max}.')
            options['UCI_Elo']=settings.elo
        if human:
            options.update(Elo=settings.human_elo,Temperature=0)
        engine.configure(options)
        limit = chess.engine.Limit(nodes=1) if human else chess.engine.Limit(time=settings.seconds) if tiny else search_limit(settings,board)
        started=time.monotonic()
        count=min(board.legal_moves.count(),board.legal_moves.count() if flounder else max(settings.multipv,4 if limited else 8 if settings.style not in ('Balanced','Maximum strength') else 1))
        if 'MultiPV' not in engine.options and count>1:
            raise ValueError('This engine supports one recommendation only. Set Candidate moves to 1.')
        count=min(count,engine.options['MultiPV'].max) if 'MultiPV' in engine.options else 1
        with engine.analysis(board, limit, multipv=count if 'MultiPV' in engine.options else None) as analysis:
            with self.lock:
                self.analysis = analysis
                if self.cancelled.is_set():
                    analysis.stop()
            last_update=0
            for info in analysis:
                now=time.monotonic()
                if (self.on_update and not limited and not human and not flounder and settings.style in ('Balanced','Maximum strength') and info.get('multipv',1)==1 and info.get('depth',0)>=8
                        and now-last_update>=.08 and not self.cancelled.is_set()):
                    infos=[dict(i) for i in analysis.multipv if i.get('pv') and 'score' in i
                           and not i.get('lowerbound') and not i.get('upperbound')]
                    if infos:
                        self.on_update(summarize(board,infos,engine.id.get('name','UCI engine')))
                        last_update=now
            lines = list(analysis.multipv)
            selected=analysis.wait().move
            with self.lock:
                self.analysis = None
        if self.cancelled.is_set():
            return None
        lines=[info for info in lines if info.get('pv')]
        if tiny and selected and not lines:lines=[{'pv':[selected]}]
        objective=summarize(board,lines[:1],engine.id.get('name','UCI engine'),allow_unscored=tiny)['lines'][0] if lines else None
        # A limited engine's bestmove is its chosen recommendation. MultiPV is
        # still ordered by objective search score, so use bestmove explicitly.
        if limited and selected:
            chosen=[info for info in lines if info.get('pv') and info['pv'][0]==selected]
            if not chosen:raise ValueError('Engine did not return analysis for its selected move. Increase think time or candidates.')
            lines=chosen+[info for info in lines if info not in chosen]
        if lines and flounder:
            index=flounder_index(board,lines,settings.human_elo);lines=[lines[index]]+lines[:index]+lines[index+1:];selected=lines[0]['pv'][0]
        if lines and settings.style not in ('Balanced','Maximum strength') and not tiny:
            index=style_index(board,lines,settings.style);lines=[lines[index]]+lines[:index]+lines[index+1:];selected=lines[0]['pv'][0]
        result=summarize(board,lines[:settings.multipv],engine.id.get("name","UCI engine"),allow_unscored=tiny)
        if objective:result['evaluation']=objective
        result['chosen_move']=selected.uci() if selected else ''
        result['recommendation_type']='human prediction' if human else 'strength-limited choice' if limited else 'Flounder sampled recommendation' if flounder else 'native bot recommendation' if tiny else 'style-ranked recommendation' if settings.style not in ('Balanced','Maximum strength') else 'best moves'
        if human:
            result['evaluation_kind']='human-game outcome estimate'
            for line in result['lines']:
                line['advantage']='Maia human-game outcome estimate'
            if 'evaluation' in result:result['evaluation']['advantage']='Maia human-game outcome estimate'
        else:result['evaluation_kind']='not supplied by this bot' if tiny else 'engine search evaluation'
        result['configuration']={'kind':settings.engine_kind,'strength':settings.strength,'skill':settings.skill,'elo':settings.elo,'human_elo':settings.human_elo,'style':settings.style,'engine_id':settings.engine_id}
        result['elapsed']=time.monotonic()-started
        result['limits']={'mode':settings.mode,'seconds':settings.seconds,'depth':settings.depth,
                          'threads':settings.threads,'multipv':settings.multipv,'hash_mb':settings.hash_mb,'effective_seconds':limit.time,'effective_depth':limit.depth}
        return result


def search_limit(settings,board=None):
    if settings.mode=='Adaptive':
        moves=board.legal_moves.count() if board else 25
        tactical=bool(board and (board.is_check() or any(board.is_capture(move) for move in board.legal_moves)))
        factor=min(1.,.35+moves/90+(.2 if tactical else 0))
        return chess.engine.Limit(time=max(.1,settings.seconds*factor),depth=min(settings.depth,max(6,8+moves//8+(2 if tactical else 0))))
    return chess.engine.Limit(time=settings.seconds if settings.mode != "Depth" else None,
                              depth=settings.depth if settings.mode != "Time" else None)


def summarize(board, infos, engine_name,allow_unscored=False):
    lines = []
    for info in infos:
        pv = info.get("pv", [])
        if not pv or ("score" not in info and not allow_unscored):
            continue
        score = info['score'].white() if 'score' in info else None
        cp,mate=(score.score(mate_score=100000),score.mate()) if score else (None,None)
        probe = board.copy()
        moves = []
        for move in pv[:12]:
            if move not in probe.legal_moves:
                break
            prefix = f"{probe.fullmove_number}." if probe.turn else (f"{probe.fullmove_number}..." if not moves else "")
            moves.append(prefix + probe.san(move))
            probe.push(move)
        reply = ""
        if len(pv) > 1:
            reply_board = board.copy()
            reply_board.push(pv[0])
            reply = reply_board.san(pv[1]) + " — " + describe_move(reply_board, pv[1])
        wdl = info.get("wdl")
        wdl_text = ""
        if wdl:
            values = wdl.white()
            total = sum(values)
            if total:
                wdl_text = f"White win {values.wins/total:.0%} · draw {values.draws/total:.0%} · Black win {values.losses/total:.0%}"
        lines.append({"move": pv[0].uci(), "san": board.san(pv[0]), "cp": cp, "mate": mate,
                      "score": (f"M{abs(mate)} {'White' if mate > 0 else 'Black'}" if mate is not None else f"{cp/100:+.2f}" if cp is not None else "—"),
                      "depth": info.get("depth", 0), "pv": " ".join(moves), "description": describe_move(board, pv[0]),
                      "reply": reply, "reply_move": pv[1].uci() if len(pv)>1 else "",
                      "pv_moves": [move.uci() for move in pv[:12]],
                      "future_move": pv[2].uci() if len(pv)>2 else "",
                      "future_simple": describe_continuation(board,[move.uci() for move in pv[:3]])["future_simple"],
                      "simple": simple_move(board,pv[0]),
                      "reply_simple": simple_move(reply_board,pv[1]) if len(pv)>1 else "",
                      "insights": move_insights(board, pv[0]),
                      "advantage": advantage(cp, mate) if cp is not None else "This bot does not provide an evaluation", "wdl": wdl_text})
    if not lines:
        raise ValueError("The engine returned no move. Try a longer thinking time.")
    return {"fen": board.fen(), "engine": engine_name, "lines": lines}


def describe_continuation(board,moves):
    probe=board.copy();pv=[];reply='';reply_simple='';future_simple=''
    for index,uci in enumerate(moves):
        move=chess.Move.from_uci(uci)
        if move not in probe.legal_moves:break
        prefix=f'{probe.fullmove_number}.' if probe.turn else (f'{probe.fullmove_number}...' if not pv else '')
        san=probe.san(move);pv.append(prefix+san)
        if index==1:reply=san+' — '+describe_move(probe,move);reply_simple=simple_move(probe,move)
        if index==2:future_simple=simple_move(probe,move)
        probe.push(move)
    return {'pv':' '.join(pv),'pv_moves':list(moves),'reply':reply,'reply_move':moves[1] if len(moves)>1 else '',
            'reply_simple':reply_simple,'future_move':moves[2] if len(moves)>2 else '', 'future_simple':future_simple}
