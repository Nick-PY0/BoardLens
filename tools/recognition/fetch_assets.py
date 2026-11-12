"""Fetch reference artwork for local recognition tests; do not redistribute artwork."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,re,urllib.request,time,hashlib
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reference-assets';OUT.mkdir(exist_ok=True)
base='https://raw.githubusercontent.com/lichess-org/lila/'+(ROOT/'lila-source-commit.txt').read_text().strip()+'/'
pieces=re.findall(r'PieceSet\("([^"]+)"',(ROOT/'PieceSet.scala').read_text());flat=pieces[:pieces.index('Basic')];three=pieces[pieces.index('Basic'):]
themes=re.findall(r'Theme\("([^"]+)", "([^"]+)"',(ROOT/'Theme.scala').read_text());cfg=json.loads((ROOT/'chesscom-reference-config.json').read_text());templates=cfg['common']['url-templates'];jobs=[];catalog=[]
letters='KQRBNP';names=['King','Queen','Rook','Bishop','Knight','Pawn']
for group,sets in [('lichess-2d',flat),('lichess-3d',three)]:
 for name in sets:
  entry={'id':group+'/'+name,'kind':'pieces','projection':'3d-sprite' if group.endswith('3d') else 'flat','site':'lichess','name':name,'files':{}};catalog.append(entry)
  for color in 'wb':
   for ch,full in zip(letters,names):
    code=color+ch
    path=('public/piece/'+name+'/'+code+('.webp' if name=='monarchy' else '.svg')) if group.endswith('2d') else 'public/images/staunton/piece/'+name+'/'+('White' if color=='w' else 'Black')+'-'+full+'.webp'
    dest=OUT/group/name/(code+Path(path).suffix);entry['files'][code]=str(dest.relative_to(OUT));jobs.append((base+path,dest))
for name,details in cfg['pieces']['collections'].items():
 entry={'id':'chesscom/'+name,'kind':'pieces','projection':'3d-sprite' if name.startswith('3d_') else 'flat','site':'chess.com','name':details['readable_name'],'files':{}};catalog.append(entry)
 for color in 'wb':
  for ch in letters:
   code=color+ch;url=templates[details['url-template']].format(collection=name,size=150,name=code.lower());dest=OUT/'chesscom'/name/(code+'.png');entry['files'][code]=str(dest.relative_to(OUT));jobs.append((url,dest))
for name,file in themes:
 path=('public/images/staunton/board/' if file.endswith('.webp') else 'public/images/board/')+file;dest=OUT/'boards/lichess'/file;catalog.append({'id':'board-lichess/'+name,'kind':'board','projection':'3d-sprite' if file.endswith('.webp') else 'flat','site':'lichess','name':name,'file':str(dest.relative_to(OUT))});jobs.append((base+path,dest))
for name,details in cfg['boards']['collections'].items():
 url=templates[details['url-template']].format(collection=name,size=200);dest=OUT/'boards/chesscom'/(name+Path(url).suffix);catalog.append({'id':'board-chesscom/'+name,'kind':'board','projection':'flat','site':'chess.com','name':details['readable_name'],'file':str(dest.relative_to(OUT))});jobs.append((url,dest))
def get(job):
 url,path=job
 if path.exists() and path.stat().st_size==2000000:path.unlink()
 if path.exists():return {'url':url,'path':str(path.relative_to(OUT)),'ok':True,'cached':True}
 try:
  if '/disguised/' in url:
   url=url.rsplit('/',1)[0]+'/'+path.stem[0]+'.svg'
  request=urllib.request.Request(url,headers={'User-Agent':'BoardLens-theme-recognition-tests/1.0'})
  with urllib.request.urlopen(request,timeout=18) as r:data=r.read(32*1024*1024+1)
  assert len(data)<=32*1024*1024
  assert len(data)>40 and not data.startswith(b'<!DOCTYPE html')
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
  return {'url':url,'path':str(path.relative_to(OUT)),'ok':True,'sha256':hashlib.sha256(data).hexdigest()}
 except Exception as e:return {'url':url,'path':str(path.relative_to(OUT)),'ok':False,'error':str(e)}
results=[]
with ThreadPoolExecutor(max_workers=8) as pool:
 for i,f in enumerate(as_completed([pool.submit(get,j) for j in jobs]),1):
  results.append(f.result())
  if i%100==0:print(i,'/',len(jobs),flush=True)
for entry in catalog:entry['downloaded']=all((OUT/f).is_file() for f in entry.get('files',{}).values()) if entry['kind']=='pieces' else (OUT/entry['file']).is_file()
(ROOT/'catalog.json').write_text(json.dumps({'sources':['https://github.com/lichess-org/lila/blob/master/modules/pref/src/main/PieceSet.scala','https://github.com/lichess-org/lila/blob/master/modules/pref/src/main/Theme.scala','https://github.com/GiorgioMegrelli/chess.com-boards-and-pieces/blob/v2.x/default-config.json'],'entries':catalog},indent=2));(ROOT/'downloads.json').write_text(json.dumps(results,indent=2));print('Done',sum(x['ok'] for x in results),'of',len(results),flush=True)
