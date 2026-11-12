from train_context import *
x=np.load(DATA/'contexts.npy',mmap_mode='r');y=np.load(DATA/'context-labels.npy',mmap_mode='r');z=np.load(DATA/'context-projection.npy',mmap_mode='r');val=np.load(DATA/'context-validation.npy',mmap_mode='r');device='mps';model=ContextNet().to(device);model.load_state_dict(torch.load(ROOT/'context-net.pt',map_location=device,weights_only=True));opt=torch.optim.AdamW(model.parameters(),lr=.00025,weight_decay=.0001);rng=np.random.default_rng(80601);train=np.flatnonzero(~val);validation=np.flatnonzero(val);batch=256;start=time.monotonic()
for epoch in range(2):
 model.train();rng.shuffle(train);loss_sum=0
 for at in range(0,len(train),batch):
  ids=train[at:at+batch];xb=torch.from_numpy(np.array(x[ids])).to(device,dtype=torch.float32).div_(255);yb=torch.from_numpy(np.array(y[ids])).to(device);zb=torch.from_numpy(np.array(z[ids])).to(device);logits,projection=model(xb);mask=yb!=0;loss=F.cross_entropy(logits,yb)+.1*F.binary_cross_entropy_with_logits(projection[mask,0],zb[mask]);opt.zero_grad();loss.backward();opt.step();loss_sum+=float(loss.detach().cpu())*len(ids)
 model.eval();correct=0
 with torch.no_grad():
  for at in range(0,len(validation),batch):
   ids=validation[at:at+batch];pred=model(torch.from_numpy(np.array(x[ids])).to(device,dtype=torch.float32).div_(255))[0].argmax(1).cpu().numpy();correct+=int((pred==np.array(y[ids])).sum())
 print(json.dumps({'epoch':epoch+7,'loss':loss_sum/len(train),'accuracy':correct/len(validation),'seconds':time.monotonic()-start}),flush=True);torch.save(model.cpu().state_dict(),ROOT/f'context-net-{epoch+7}.pt');model.to(device)
