"""Explicit, named analysis presets; no engine downloads or implicit fallback."""
from copy import deepcopy
import uuid
from .core import data_dir
from .storage import atomic_json

FIELDS=('playing_style','strength_mode','engine_skill','engine_elo','human_elo','seconds','depth','mode','threads','hash_mb','multipv','early_suggestions','arrow_count','show_white','show_black','show_reply','rank_best','rank_second','rank_others','arrow_labels','only_my_color','stick_to_move','steady_arrows','dashed_reply','threats_enabled','threat_attacks','threat_mates')
DEFAULTS=[
 {'id':'quick','name':'Quick analysis','builtin':True,'settings':{'engine_identity':'stockfish','mode':'Time','seconds':.3,'multipv':1,'arrow_count':1,'threads':1,'hash_mb':64,'strength_mode':0,'playing_style':0,'rank_best':True,'rank_second':False,'rank_others':False,'steady_arrows':True}},
 {'id':'deep','name':'Deep analysis','builtin':True,'settings':{'engine_identity':'stockfish','mode':'Time + depth','seconds':5.,'depth':22,'multipv':3,'arrow_count':3,'strength_mode':0,'playing_style':0,'rank_best':True,'rank_second':True,'rank_others':True,'steady_arrows':True}},
]

class PresetStore:
    def __init__(self,path=None):
        import json
        self.path=path or data_dir()/'analysis-presets.json'
        try:self.custom=json.loads(self.path.read_text())
        except (OSError,ValueError):self.custom=[]
        if not isinstance(self.custom,list):self.custom=[]
        self.custom=[p for p in self.custom if isinstance(p,dict) and isinstance(p.get('id'),str) and isinstance(p.get('name'),str) and isinstance(p.get('settings'),dict) and p.get('builtin') is False and p['id'] not in {v['id'] for v in DEFAULTS}|{'coach'} and not set(p['settings'])-(set(FIELDS)|{'engine_identity','custom_engine'})]
    def list(self):return deepcopy(DEFAULTS+self.custom)
    def get(self,identity):
        for item in self.list():
            if item['id']==identity:return item
        raise ValueError('That preset is unavailable.')
    def save(self,name,values,identity=None):
        name=str(name).strip()
        if not name or len(name)>60 or any(ord(c)<32 for c in name):raise ValueError('Use a preset name between 1 and 60 characters on one line.')
        if identity and self.get(identity).get('builtin'):raise ValueError('Save a new copy of a built-in preset.')
        if any(item['name'].casefold()==name.casefold() and item['id']!=identity for item in self.list()):raise ValueError('A preset already uses that name.')
        allowed=set(FIELDS)|{'engine_identity','custom_engine'}
        if not isinstance(values,dict) or set(values)-allowed:raise ValueError('Unsupported preset settings.')
        item={'id':identity or uuid.uuid4().hex,'name':name,'builtin':False,'settings':deepcopy(values)}
        self.custom=[p for p in self.custom if p['id']!=item['id']]+[item];atomic_json(self.path,self.custom);return item['id']
    def delete(self,identity):
        if self.get(identity).get('builtin'):raise ValueError('Built-in presets cannot be removed.')
        self.custom=[p for p in self.custom if p['id']!=identity];atomic_json(self.path,self.custom)
