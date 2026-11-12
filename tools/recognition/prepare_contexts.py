"""Generate labeled, reproducible context crops from local reference artwork."""
from pathlib import Path
import json,random,hashlib,os
import numpy as np
from PIL import Image,ImageEnhance,ImageDraw
from render_reference import ROOT,PIECES,BOARDS,artwork,render,START,LABELS

DATA=Path(os.environ.get('BOARDLENS_CORPUS',str(Path.home()/'.cache/BoardLens/recognition-v3')));DATA.mkdir(parents=True,exist_ok=True)
rng=random.Random(71403)
styles=[];ambiguous=[]
for s in PIECES:
 distinct=[]
 for color in 'wb':
  distinct.append(len({hashlib.sha256(artwork(s['files'][color+c]).resize((96,96)).tobytes()).hexdigest() for c in 'KQRBNP'}))
 if min(distinct)<6:ambiguous.append(s['id'])
 else:styles.append(s)
print('Training styles:',len(styles),'visually ambiguous:',ambiguous,flush=True)
boards=[b for b in BOARDS if b['projection']=='flat']
count=len(styles)*48;n=count*64
x=np.lib.format.open_memmap(DATA/'contexts.npy',mode='w+',dtype=np.uint8,shape=(n,96,64));y=np.lib.format.open_memmap(DATA/'context-labels.npy',mode='w+',dtype=np.int64,shape=(n,));z=np.lib.format.open_memmap(DATA/'context-projection.npy',mode='w+',dtype=np.float32,shape=(n,))
validation=np.lib.format.open_memmap(DATA/'context-validation.npy',mode='w+',dtype=np.bool_,shape=(n,))
for boardid in range(count):
 style=styles[boardid%len(styles)];cycle=boardid//len(styles);bg=boards[(cycle*7+boardid%len(styles)*13)%len(boards)]
 if cycle%12==0:placement=START
 else:
  cells=['.']*64
  for i in rng.sample(range(64),rng.randint(12,34)):cells[i]=rng.choice('QRBNPqrbnp')
  a,b=rng.sample(range(64),2);cells[a]='K';cells[b]='k';placement=''.join(cells)
 flip=bool(rng.getrandbits(1));size=rng.choice([256,320,384,448,512])
 image,rect,shown=render(style,bg,placement,flip,size,highlight=cycle%5==0)
 if cycle%4==0:image=ImageEnhance.Brightness(image).enhance(rng.uniform(.7,1.25))
 if cycle%7==0:
  draw=ImageDraw.Draw(image,'RGBA');xx,yy,w,h=rect
  for row in range(8):draw.text((xx+2,yy+row*h/8+1),str(8-row),fill=(55,85,55,220))
 xx,yy,w,h=rect;cell=w/8
 for index,ch in enumerate(shown):
  row,col=divmod(index,8);cx=xx+(col+.5)*w/8;cy=yy+(row+.5)*h/8
  # Screen-space crop: crowns stay visible even when the board plane is compressed.
  box=(cx-.75*cell,cy-1.5*cell,cx+.75*cell,cy+.65*cell)
  # Crop padding is intentional when a far-rank crown extends beyond the frame.
  patch=image.crop(tuple(round(v) for v in box)).resize((64,96),Image.Resampling.BILINEAR).convert('L')
  at=boardid*64+index;x[at]=np.asarray(patch);y[at]=LABELS.index(ch);z[at]=int(style['projection']=='3d-sprite');validation[at]=cycle%10==9
 if boardid%100==0:
  print(boardid,'/',count,style['id'],flush=True);x.flush()
x.flush();y.flush();z.flush();validation.flush();(ROOT/'context-corpus.json').write_text(json.dumps({'seed':71403,'boards':count,'tiles':n,'styles':[s['id'] for s in styles],'ambiguous_styles':ambiguous,'shape':[96,64],'crop':[-.75,-1.5,.75,.65],'board_textures':[b['id'] for b in boards]},indent=2));print('Ready',n,'tiles',flush=True)
