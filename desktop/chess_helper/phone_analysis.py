"""Optional compute backend for phone-screen positions; never edits desktop game/settings."""
from dataclasses import replace
from copy import deepcopy
import math,threading,time
import chess
from PySide6.QtCore import QObject,Signal
from .core import SearchSettings
from .engine import EngineJob,EngineSession
from . import engine_config,engine_library

class PhoneAnalysis(QObject):
    completed=Signal(int,str,object,str,bool)
    def __init__(self,window):
        super().__init__(window);self.window=window;self.generation=0;self.sessions=[EngineSession(),EngineSession()];self.jobs=[];self.state={};self.closed=False;self.completed.connect(self.finish)
    def request(self,payload):
        fen=payload.get('fen');request=payload.get('request_id')
        if not isinstance(fen,str) or len(fen)>160 or not isinstance(request,str) or not 1<=len(request)<=80:raise ValueError('Invalid phone position request.')
        board=chess.Board(fen)
        if not board.is_valid() or board.is_game_over():raise ValueError('A playable legal position is required.')
        def entry(key,default):
            identity=payload.get(key,default)
            if identity not in engine_library.BY_ID:raise ValueError('Unknown phone engine.')
            item=engine_library.BY_ID[identity]
            return item,engine_config.command(self.window,engine_library.ENTRIES.index(item))
        chosen,path=entry('engine','stockfish');evaluator,eval_path=entry('evaluator','stockfish')
        if evaluator.kind=='tiny':raise ValueError('This bot does not provide an evaluation.')
        def number(key,default,low,high,integer=False):
            value=payload.get(key,default)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high or integer and value!=int(value):raise ValueError('Invalid '+key)
            return int(value) if integer else value
        seconds=number('seconds',.5,.05,30);depth=number('depth',18,1,40,True);count=number('moves',1,1,10,True);rating=number('rating',1500,600,2600,True)
        threads=number('threads',1,1,64,True);skill=number('skill',20,0,20,True)
        mode=payload.get('mode','Time + depth')
        if mode not in ('Time','Depth','Time + depth'):raise ValueError('Invalid search limit.')
        prediction_plies=number('prediction_plies',3,1,12,True);prediction_seconds=number('prediction_seconds',3.,.1,60)
        predict=payload.get('predict',True)
        if not isinstance(predict,bool):raise ValueError('Invalid prediction toggle.')
        settings=SearchSettings(seconds=seconds,depth=depth,mode='Time' if chosen.kind=='tiny' else mode,multipv=1 if chosen.kind=='tiny' else count,threads=threads,hash_mb=64,skill=skill,strength='Skill level' if chosen.kind=='stockfish' and skill<20 else 'Full strength',engine_kind=chosen.identity if chosen.kind=='tiny' else chosen.kind,engine_id=chosen.identity,human_elo=rating,predict_continuations=predict,prediction_plies=prediction_plies,prediction_seconds=prediction_seconds)
        self.cancel();token=self.generation;self.state={'request_id':request,'fen':board.fen(),'status':'thinking','recommendation':None,'evaluation':None,'error':'','recommendation_done':False,'evaluation_done':False}
        profiles=[('recommendation',path,settings),('evaluation',eval_path,replace(settings,engine_kind='stockfish' if evaluator.kind=='flounder' else evaluator.kind,engine_id=evaluator.identity,seconds=.3,depth=18,multipv=1,threads=1,strength='Full strength',mode='Time + depth',predict_continuations=False))]
        for slot,(kind,command,limits) in enumerate(profiles):
            job=EngineJob();job.session=self.sessions[slot];self.jobs.append(job)
            if kind=='recommendation':job.on_update=lambda result,token=token:self.completed.emit(token,'recommendation',deepcopy(result),'',False)
            def run(job=job,kind=kind,command=command,limits=limits,token=token):
                try:result,error=job.run(command,board,limits),''
                except Exception as exc:result,error=None,str(exc)
                if not self.closed:self.completed.emit(token,kind,result,error,True)
            threading.Thread(target=run,daemon=True,name='BoardLens-phone-position').start()
        return {'request_id':request,'accepted':True}
    def finish(self,token,kind,result,error,finished=True):
        if self.closed or token!=self.generation:return
        if error:self.state['error']=error;self.state['status']='error'
        elif result:
            self.state[kind]=result
            if finished:self.state[kind+'_done']=True
            if self.state.get('recommendation_done') and self.state.get('evaluation_done'):self.state['status']='ready'
    def cancel(self):
        self.generation+=1
        for job in self.jobs:job.cancel()
        self.jobs=[]
    def snapshot(self):return deepcopy(self.state)
    def close(self):
        self.closed=True;self.cancel()
        for session in self.sessions:session.close()
