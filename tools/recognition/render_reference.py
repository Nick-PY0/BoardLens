"""Render labeled reference boards for theme tests. Artwork remains local-only."""
from pathlib import Path
from functools import lru_cache
import json,random,io
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
import resvg_py

ROOT=Path(__file__).resolve().parent;ASSETS=ROOT/'reference-assets'
CATALOG=json.loads((ROOT/'catalog.json').read_text())['entries']
PIECES=[e for e in CATALOG if e['kind']=='pieces' and e['downloaded']]
BOARDS=[e for e in CATALOG if e['kind']=='board' and e['downloaded']]
LABELS='.KQRBNPkqrbnp'
START='rnbqkbnrpppppppp................................PPPPPPPPRNBQKBNR'
ITALIAN='r.bqk.nrpppp.ppp..n.......b.p.....B.P........N..PPPP.PPPRNBQK..R'

@lru_cache(maxsize=2000)
def artwork(path):
 p=ASSETS/path
 if p.suffix=='.svg':
  root=ET.fromstring(p.read_text());root.set('width','180');root.set('height','180')
  data=resvg_py.svg_to_bytes(svg_string=ET.tostring(root,encoding='unicode'),width=180,height=180)
  return Image.open(io.BytesIO(data)).convert('RGBA')
 return Image.open(p).convert('RGBA')

@lru_cache(maxsize=2000)
def sprite(path,width,height):
 return artwork(path).resize((width,height),Image.Resampling.LANCZOS)

def render(style,board,placement=START,flipped=False,size=512,highlight=False):
 three=style['projection']=='3d-sprite'
 height=round(size*.9078571) if three and style['site']=='lichess' else size
 x,y=round(size*.14),round(size*.24) if three else round(size*.14)
 image=Image.new('RGBA',(size+2*x,height+y+round(size*.14)),(36,39,43,255))
 bg=artwork(board['file']).resize((size,height),Image.Resampling.BILINEAR)
 image.alpha_composite(bg,(x,y))
 # CSS geometry from Lichess's board-3d.scss; Chess.com 3D sprites use their
 # natural aspect and extend above the square. The board plane stays labeled.
 shown=placement[::-1] if flipped else placement
 if highlight:
  draw=ImageDraw.Draw(image,'RGBA')
  for index in [27,35]:
   row,col=divmod(index,8);draw.rectangle((x+col*size/8,y+row*height/8,x+(col+1)*size/8,y+(row+1)*height/8),fill=(190,215,35,95))
 for index,ch in enumerate(shown):
  if ch=='.':continue
  row,col=divmod(index,8);code=('w' if ch.isupper() else 'b')+ch.upper();path=style['files'][code]
  if three and style['site']=='lichess':
   width=round(size*.16741);hh=round(height*.23563);left=round(x+col*size/8-size*.0185);top=round(y+row*height/8-height*.091)
  elif three:
   width=round(size/8);ratio=artwork(path).height/artwork(path).width;hh=round(width*ratio);left=round(x+col*size/8);top=round(y+(row+1)*height/8-hh)
  else:
   width=round(size/8);hh=round(height/8);left=round(x+col*size/8);top=round(y+row*height/8)
  image.alpha_composite(sprite(path,width,hh),(left,top))
 return image.convert('RGB'),(x,y,size,height),shown

def tiles(image,rect):
 x,y,w,h=rect
 board=np.asarray(image.crop((x,y,x+w,y+h)).resize((256,256),Image.Resampling.BILINEAR),dtype=np.float32)
 gray=(board[:,:,0]*.299+board[:,:,1]*.587+board[:,:,2]*.114)/255
 return gray.reshape(8,32,8,32).transpose(0,2,1,3)[::-1].reshape(64,1024).copy()

def contexts(image,rect):
 # Keep the crown and the base together, including the space above the tile.
 x,y,w,h=rect;patches=[]
 for row in range(8):
  for col in range(8):
   box=(x+(col-.25)*w/8,y+(row-1.1)*h/8,x+(col+1.25)*w/8,y+(row+1.2)*h/8)
   patch=image.resize((64,96),Image.Resampling.BILINEAR,box=box).convert('L')
   patches.append(np.asarray(patch,np.uint8))
 return np.stack(patches)

if __name__=='__main__':
 for i,style in enumerate([next(p for p in PIECES if p['id']=='lichess-3d/Basic'),next(p for p in PIECES if p['id']=='chesscom/3d_wood')]):
  image,rect,shown=render(style,BOARDS[0]);image.save(ROOT/f'render-3d-{i}.png');print(style['id'],rect,len(shown))
