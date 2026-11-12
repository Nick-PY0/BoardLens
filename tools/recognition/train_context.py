"""Train context-aware piece identification; no downloaded artwork is shipped."""
from pathlib import Path
import json,time,os
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('BOARDLENS_CORPUS',str(Path.home()/'.cache/BoardLens/recognition-v3')))
torch.set_num_threads(2);torch.manual_seed(71403)
class ContextNet(nn.Module):
 def __init__(self):
  super().__init__()
  self.features=nn.Sequential(nn.Conv2d(1,24,3,padding=1),nn.BatchNorm2d(24),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(24,40,3,padding=1),nn.BatchNorm2d(40),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(40,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(64,64,3,padding=1),nn.ReLU(),nn.AvgPool2d(2))
  self.shared=nn.Sequential(nn.Flatten(),nn.Linear(64*6*4,160),nn.ReLU(),nn.Dropout(.1));self.classes=nn.Linear(160,13);self.projection=nn.Linear(160,1)
 def forward(self,x):
  h=self.shared(self.features(x.reshape(-1,1,96,64)));return self.classes(h),self.projection(h)
class Export(nn.Module):
 def __init__(self,net):super().__init__();self.net=net
 def forward(self,x):
  y,z=self.net(x);return F.softmax(y,dim=1),torch.sigmoid(z)
if __name__=='__main__':
 x=np.load(DATA/'contexts.npy',mmap_mode='r');y=np.load(DATA/'context-labels.npy',mmap_mode='r');z=np.load(DATA/'context-projection.npy',mmap_mode='r');val=np.load(DATA/'context-validation.npy',mmap_mode='r')
 device='mps' if torch.backends.mps.is_available() else 'cpu';model=ContextNet().to(device);opt=torch.optim.AdamW(model.parameters(),lr=.0015,weight_decay=.0001);rng=np.random.default_rng(71403);train=np.flatnonzero(~val);validation=np.flatnonzero(val);batch=256;epochs=int(os.getenv('EPOCHS','6'));history=[];start=time.monotonic()
 print('device',device,'train',len(train),'validation',len(validation),'parameters',sum(p.numel() for p in model.parameters()),flush=True)
 for epoch in range(epochs):
  model.train();rng.shuffle(train);loss_sum=0
  for at in range(0,len(train),batch):
   ids=train[at:at+batch];xb=torch.from_numpy(np.array(x[ids])).to(device,dtype=torch.float32).div_(255);yb=torch.from_numpy(np.array(y[ids])).to(device);zb=torch.from_numpy(np.array(z[ids])).to(device)
   xb=(xb*(.85+torch.rand(len(ids),1,1,device=device)*.3)+(torch.rand(len(ids),1,1,device=device)-.5)*.08).clamp(0,1)
   logits,projection=model(xb);mask=yb!=0;loss=F.cross_entropy(logits,yb)+.1*F.binary_cross_entropy_with_logits(projection[mask,0],zb[mask]);opt.zero_grad();loss.backward();opt.step();loss_sum+=float(loss.detach().cpu())*len(ids)
  model.eval();correct=0;errors=np.zeros(13,dtype=int);total=np.zeros(13,dtype=int)
  with torch.no_grad():
   for at in range(0,len(validation),batch):
    ids=validation[at:at+batch];xb=torch.from_numpy(np.array(x[ids])).to(device,dtype=torch.float32).div_(255);pred=model(xb)[0].argmax(1).cpu().numpy();truth=np.array(y[ids]);correct+=int((pred==truth).sum())
    total+=np.bincount(truth,minlength=13);errors+=np.bincount(truth[pred!=truth],minlength=13)
  row={'epoch':epoch+1,'loss':loss_sum/len(train),'accuracy':correct/len(validation),'errors':errors.tolist(),'seconds':time.monotonic()-start};history.append(row);print(json.dumps(row),flush=True);torch.save(model.cpu().state_dict(),ROOT/'context-net.pt');model.to(device)
  (ROOT/'training.json').write_text(json.dumps({'labels':'.KQRBNPkqrbnp','device':device,'history':history},indent=2))
 model.cpu().eval();torch.onnx.export(Export(model),torch.zeros(1,6144),ROOT/'context-net.onnx',input_names=['patches'],output_names=['probs','projection'],dynamic_axes={'patches':{0:'batch'},'probs':{0:'batch'},'projection':{0:'batch'}},opset_version=17,dynamo=False)
 print('Exported',flush=True)
