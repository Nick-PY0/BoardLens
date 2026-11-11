"""Offline question retrieval over documented, feature-specific answers."""
import json,math,re,unicodedata
from collections import Counter
from difflib import SequenceMatcher,get_close_matches
from pathlib import Path

STOP=set('a an the i me my we you your it its is are be been how what why do does did can could would should to of for in on at with and or please when where which there this that not just still really'.split())
GROUPS=[('phone','mobile','android','tablet','ipad','companion'),('slow','delay','lag','latency','speed','fast','faster','refresh'),('save','saved','remember','persist','forget','reset','restore'),('arrow','arrows','highlight','hints','suggestion','suggestions'),('board','boards','position','chessboard'),('freeze','frozen','stick','steady','flicker','switching','changing'),('connect','connection','pair','pairing','link','offline','disconnected'),('engine','stockfish','analysis','thinking','calculate'),('key','keys','shortcut','shortcuts','keyboard','keybind','keybinds'),('white','black','color','colour','side','orientation'),('maia','maya','human','humanlike'),('missing','invisible','vanish','disappear','disappearing','hidden'),('install','download','setup','model','models'),('error','failed','failure','broken','repair','fix')]
GROUPS += [('preferences','settings','options','choices','configuration'),('forget','forgets','forgot','forgetting','remember','remembering','losing','lost','reset','resets'),('quit','exit','close','closing','reopen','reopening','restart','restarted'),('cyan','turquoise'),('think','thinking','calculate','calculating','search','searching')]
SYNONYMS={word:set(group) for group in GROUPS for word in group}

def normalize(value):
    value=unicodedata.normalize('NFKD',value.casefold()).replace('’',"'")
    return ' '.join(re.findall(r'[a-z0-9]+',value))
def words(value):return {w for w in normalize(value).split() if w not in STOP and len(w)>1}
def topics():return json.loads((Path(__file__).parent/'assets/ui/help_topics.json').read_text())

class HelpIndex:
    def __init__(self,items=None):
        self.items=items or topics();self.vocabulary=set();self.tokens={};counts=Counter()
        for item in self.items:
            text=' '.join([item['title'],item['summary'],item.get('details',''),*item.get('steps',[]),*item.get('questions',[]),*item.get('aliases',[])])
            tokens=words(text);self.tokens[item['id']]=tokens;counts.update(tokens);self.vocabulary.update(tokens)
        self.weights={t:1+math.log((len(self.items)+1)/(count+1)) for t,count in counts.items()}
    def search(self,query,category='All sections'):
        raw=normalize(query);query_words=words(query)
        if not query_words:return [item for item in self.items if category=='All sections' or item['category']==category]
        corrected=set()
        for token in query_words:
            corrected.add(token)
            if token not in self.vocabulary and token not in SYNONYMS and len(token)>=3:
                corrected.update(get_close_matches(token,self.vocabulary,n=1,cutoff=.85 if len(token)==3 else .8))
        expanded=set(corrected)
        for token in corrected:expanded.update(SYNONYMS.get(token,()))
        results=[]
        for item in self.items:
            if category!='All sections' and item['category']!=category:continue
            tokens=self.tokens[item['id']];exact=corrected&tokens;related=(expanded&tokens)-exact
            score=sum(self.weights.get(t,1) for t in exact)+.16*sum(self.weights.get(t,1) for t in related)
            # Full-question matching and curated phrases outrank a shared word.
            for question in item.get('questions',[])+item.get('aliases',[]):
                q=normalize(question);qw=words(question)
                if q in raw or raw in q:score+=7 if len(raw)>5 else 0
                ratio=SequenceMatcher(None,raw,q).ratio()
                if ratio>.57:score=max(score,ratio*18)
                if qw and len(qw&corrected)>=2:score+=4*len(qw&corrected)/len(qw)
            score+=2*len(words(item['title'])&corrected)
            if exact or related and score>=1.2:results.append((score,item))
        return [item for score,item in sorted(results,key=lambda pair:pair[0],reverse=True) if score>=1.2][:18]
