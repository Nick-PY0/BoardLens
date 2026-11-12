"""Export pinned official Maia weights to the Android ONNX interface; check parity."""
import argparse,sys,json,hashlib,math,copy
from pathlib import Path
import numpy as np
import torch
import onnx,onnxruntime as ort
import chess
p=argparse.ArgumentParser();p.add_argument('--kind',choices=['maia2','maia3-5m','maia3-23m','maia3-79m'],required=True);p.add_argument('--package-path',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
sys.path.append(str(args.package_path));args.out.mkdir(parents=True,exist_ok=True)
torch.set_num_threads(2);torch.backends.mha.set_fastpath_enabled(False)
if args.kind=='maia2':
 from maia2.main import MAIA2Model
 from maia2.train import load_model_state_dict
 from maia2.utils import parse_args,create_elo_dict,get_all_possible_moves,board_to_tensor,map_to_category
 import maia2
 cfg=parse_args(Path(maia2.__file__).parent/'configs/maia2-training.yaml');vocab=get_all_possible_moves();elo_dict=create_elo_dict();model=MAIA2Model(len(vocab),elo_dict,cfg)
 ckpt=torch.load(args.checkpoint,map_location='cpu',weights_only=True);load_model_state_dict(model,ckpt['model_state_dict']);model.eval()
 def encode(board,rating):
  canonical=board if board.turn else board.mirror();return board_to_tensor(canonical).unsqueeze(0),torch.tensor([map_to_category(rating,elo_dict)],dtype=torch.long)
 class Wrapper(torch.nn.Module):
  def __init__(self):super().__init__();self.inner=model
  def forward(self,tokens,self_rating,opponent_rating):
   policy,_,value=self.inner(tokens,self_rating,opponent_rating);return policy,value.reshape(1,-1)
else:
 from maia3.uci import parse_args,load_model
 from maia3.model_registry import MODEL_SPECS
 from maia3.utils import get_all_possible_moves
 from maia3.dataset import tokenize_board
 cfg=parse_args(['--model',args.kind]);spec=next(s for s in MODEL_SPECS if s.name==args.kind)
 for key,value in spec.config.items():setattr(cfg,key,value)
 cfg.device='cpu';cfg.checkpoint_path=str(args.checkpoint);model=load_model(cfg);vocab=get_all_possible_moves()
 def encode(board,rating):
  tokens=tokenize_board(board);tokens=torch.cat([tokens]*8+[torch.zeros(64,1)],dim=1);return tokens.unsqueeze(0),torch.tensor([rating],dtype=torch.long)
 class Wrapper(torch.nn.Module):
  def __init__(self):super().__init__();self.inner=model
  def forward(self,tokens,self_rating,opponent_rating):
   policy,value,_=self.inner(tokens,self_rating,opponent_rating);return policy,value
# Legacy ONNX exporter does not lower aten::rms_norm; these elementary operations
# are mathematically identical to PyTorch's RMSNorm, including its default eps.
class PortableRMS(torch.nn.Module):
 def __init__(self,original):super().__init__();self.weight=original.weight;self.eps=original.eps
 def forward(self,x):return x*torch.rsqrt(x.pow(2).mean(-1,keepdim=True)+(self.eps if self.eps is not None else torch.finfo(x.dtype).eps))*self.weight
def portable(module):
 for name,child in list(module.named_children()):
  if isinstance(child,torch.nn.RMSNorm):setattr(module,name,PortableRMS(child))
  else:portable(child)
portable(model);wrapper=Wrapper().eval();sample,elo=encode(chess.Board(),1500);destination=args.out/(args.kind+'.onnx')
with torch.inference_mode():
 torch.onnx.export(wrapper,(sample,elo,elo),str(destination),input_names=['board','self_rating','opponent_rating'],output_names=['policy','value'],opset_version=18,dynamo=False)
converted=onnx.load(destination)
converted.doc_string='';converted.graph.doc_string=''
for node in converted.graph.node:node.doc_string=''
onnx.save(converted,destination);onnx.checker.check_model(converted)
session=ort.InferenceSession(str(destination),providers=['CPUExecutionProvider']);positions=[chess.Board(),chess.Board('r3k2r/ppp2ppp/2n1bn2/3qp3/3P4/2N1BN2/PPP2PPP/R2Q1RK1 b kq - 4 9'),chess.Board('4k3/P7/8/8/8/8/7p/4K3 w - - 0 1'),chess.Board('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')]
board=chess.Board();rng=np.random.default_rng(42)
for i in range(36):
 legal=list(board.legal_moves)
 if not legal:break
 board.push(legal[int(rng.integers(len(legal)))]);
 if i%4==0:positions.append(board.copy())
checks=[];golden=[];indices={m:i for i,m in enumerate(vocab)}
for board in positions:
 for rating in (900,1500,2300):
  encoded,elo=encode(board,rating)
  with torch.inference_mode():expected=wrapper(encoded,elo,elo)[0].numpy()[0]
  actual=session.run(None,{'board':encoded.numpy(),'self_rating':elo.numpy(),'opponent_rating':elo.numpy()})[0][0]
  moves=list(board.legal_moves);canonical=lambda m: m.uci() if board.turn else chess.Move(m.from_square^56,m.to_square^56,m.promotion).uci()
  legal_indices=[indices[canonical(m)] for m in moves];reference=int(np.argmax(expected[legal_indices]));predicted=int(np.argmax(actual[legal_indices]));assert reference==predicted,(args.kind,board.fen(),rating)
  error=float(np.max(np.abs(expected-actual)));checks.append({'fen':board.fen(),'rating':rating,'move':moves[reference].uci(),'max_logit_error':error})
  if rating==1500:golden.append({'fen':board.fen(),'rating':rating,'shape':list(encoded.shape),'nonzero':[[int(i),float(encoded.numpy().ravel()[i])] for i in np.flatnonzero(encoded.numpy().ravel())],'elo':int(elo[0]),'best_move':moves[reference].uci()})
name='maia2' if args.kind=='maia2' else 'maia3';(args.out/(name+'-moves.json')).write_text(json.dumps(vocab));(args.out/(args.kind+'-golden.json')).write_text(json.dumps(golden))
record={'id':args.kind,'bytes':destination.stat().st_size,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'checkpoint_sha256':hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),'input_shape':list(sample.shape),'parity':checks,'torch_version':torch.__version__,'onnx_opset':18};(args.out/(args.kind+'.json')).write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='parity'}),flush=True);print('Matched reference legal top move for',len(checks),'positions/ratings',flush=True)
