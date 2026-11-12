from pathlib import Path
import json,time,sys,os
import numpy as np,torch,onnxruntime as ort
from PIL import Image
from train_context import ContextNet,Export
from render_reference import ROOT,PIECES,BOARDS,render,START,ITALIAN,LABELS
m=ContextNet();m.load_state_dict(torch.load(ROOT/os.environ.get('CONTEXT_CHECKPOINT','context-net.pt'),map_location='cpu',weights_only=True));m.eval();torch.onnx.export(Export(m),torch.zeros(1,6144),ROOT/'context-candidate.onnx',input_names=['patches'],output_names=['probs','projection'],dynamic_axes={'patches':{0:'batch'},'probs':{0:'batch'},'projection':{0:'batch'}},opset_version=17,dynamo=False)
o=ort.SessionOptions();o.intra_op_num_threads=2;session=ort.InferenceSession(str(ROOT/'context-candidate.onnx'),o);board=next(b for b in BOARDS if b['projection']=='flat');results=[]
for style in PIECES:
 for flip,position in [(False,START),(True,ITALIAN)]:
  im,rect,expected=render(style,board,position,flip,384);x,y,w,h=rect;cell=w/8;patches=[]
  for row in range(8):
   for col in range(8):
    cx=x+(col+.5)*w/8;cy=y+(row+.5)*h/8;box=(cx-.75*cell,cy-1.5*cell,cx+.75*cell,cy+.65*cell);patch=im.crop(tuple(round(v) for v in box)).resize((64,96),Image.Resampling.BILINEAR).convert('L');patches.append(np.asarray(patch,np.float32).reshape(-1)/255)
  started=time.monotonic();p,z=session.run(None,{'patches':np.stack(patches)});guess=''.join(LABELS[i] for i in p.argmax(1));prob=p.max(1);accepted=prob.min()>=.97 and prob.mean()>=.99 and guess.count('K')==1 and guess.count('k')==1
  results.append({'style':style['id'],'flip':flip,'correct':sum(a==b for a,b in zip(expected,guess)),'exact':expected==guess,'accepted':bool(accepted),'confident_wrong':bool(accepted and guess!=expected),'min':float(prob.min()),'mean':float(prob.mean()),'ms':(time.monotonic()-started)*1000,'expected':expected,'actual':guess,'projection':float(z[np.array(list(guess))!='.'].mean())})
  print(style['id'],flip,results[-1]['correct'],bool(accepted),flush=True)
(ROOT/'theme-context-audit.json').write_text(json.dumps({'cases':results,'exact':sum(r['exact'] for r in results),'accepted':sum(r['accepted'] for r in results),'confident_wrong':sum(r['confident_wrong'] for r in results)},indent=2))
