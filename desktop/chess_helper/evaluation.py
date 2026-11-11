"""Independent evaluation jobs; recommendation providers never choose the bar."""
from collections import OrderedDict
from dataclasses import replace
import threading,time
from PySide6.QtCore import QObject,Signal
from .core import SearchSettings
from .engine import EngineJob,EngineSession
from . import engine_config,engine_library


class Evaluations(QObject):
    completed=Signal(str,int,object,str)
    changed=Signal(str)
    def __init__(self,window):
        super().__init__(window);self.window=window;self.generation=0;self.cache=OrderedDict();self.queue=OrderedDict();self.active={};self.sessions=[EngineSession(),EngineSession()];self.closed=False;self.errors={};self.completed.connect(self.finish)
    def profile(self):
        w=self.window;index=w.eval_engine.currentData();entry=engine_library.ENTRIES[index]
        settings=SearchSettings(seconds=w.eval_seconds.value(),depth=w.eval_depth.value(),mode='Time + depth',multipv=1,threads=1,hash_mb=64,engine_kind='stockfish' if entry.kind=='flounder' else entry.kind,human_elo=w.eval_human_elo.value(),engine_id=entry.identity,predict_continuations=False)
        return index,entry,settings
    def request(self,board):
        if self.closed or not board.is_valid() or board.is_game_over():return
        fen=board.fen()
        if fen in self.cache or fen in self.queue or any(v[0]==fen for v in self.active.values()):return
        if self.errors.get(fen,(0,''))[0]>time.monotonic():return
        self.queue[fen]=board.copy();self.pump()
    def pump(self):
        for slot,session in enumerate(self.sessions):
            if slot in self.active or not self.queue or self.closed:continue
            fen,board=self.queue.popitem(last=False);generation=self.generation
            try:index,entry,settings=self.profile();path=engine_config.command(self.window,index)
            except Exception as exc:self.errors[fen]=(time.monotonic()+5,str(exc));self.changed.emit(fen);continue
            job=EngineJob();job.session=session;self.active[slot]=(fen,job)
            def run(slot=slot,fen=fen,board=board,path=path,settings=settings,job=job,generation=generation):
                try:result,error=job.run(path,board,settings),''
                except Exception as exc:result,error=None,str(exc)
                if not self.closed:self.completed.emit(fen,generation,(slot,result),error)
            threading.Thread(target=run,daemon=True,name='BoardLens-evaluation').start()
    def finish(self,fen,generation,value,error):
        slot,result=value
        if generation!=self.generation or self.closed:return
        self.active.pop(slot,None)
        if error:self.errors[fen]=(time.monotonic()+5,error)
        elif result and result.get('fen')==fen:
            self.cache[fen]=result
            while len(self.cache)>160:self.cache.popitem(last=False)
            self.errors.pop(fen,None)
        self.changed.emit(fen);self.pump()
    def score(self,board,recommendation=None):
        fen=board.fen();result=self.cache.get(fen);_,entry,_=self.profile()
        if not result and recommendation and recommendation.get('fen')==fen:
            # Identical unrestricted providers may share their searched score
            # while the independent evaluator is warming up.
            chosen=engine_config.entry(self.window)
            if entry.identity==chosen.identity and chosen.kind=='stockfish' and self.window.strength_mode.currentText()=='Full strength':
                result=recommendation
        if result:
            lead=dict(result.get('evaluation',result['lines'][0]));lead.update(provider=result['engine'],kind=result.get('evaluation_kind','engine search evaluation'));return lead
        message=self.errors.get(fen,(0,''))[1]
        return {'cp':None,'mate':None,'score':'—','advantage':('Evaluation unavailable: '+message) if message else 'Waiting for '+entry.label+' evaluation','provider':entry.label,'kind':'pending','wdl':''}
    def invalidate(self):
        self.generation+=1
        for _,job in self.active.values():job.cancel()
        self.active.clear();self.cache.clear();self.queue.clear();self.errors.clear()
    def close(self):
        self.closed=True;self.invalidate()
        for session in self.sessions:session.close()
