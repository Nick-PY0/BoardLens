package app.boardlens.companion;
import android.content.Context;
import java.util.*;
import java.util.concurrent.CancellationException;
import java.util.function.BooleanSupplier;

/** All phone engines share validation, prediction and cancellation; no network inference. */
final class LocalEngines implements AutoCloseable {
 record Evaluated(String text,float whiteShare){}
 private final PhoneEngine stockfish=new PhoneEngine();private final MaiaLocal maia=new MaiaLocal();private final TinyLocal tiny=new TinyLocal();
 private volatile boolean cancelled;
 private PhoneEngine.Result one(Context c,ChessPosition board,PhoneSettings settings,String id,boolean eval,PhoneEngine.Update update)throws Exception{
  if(cancelled)throw new CancellationException();EngineCatalog.Entry engine=EngineCatalog.get(id);
  if(engine.maia())return maia.search(c,board,engine.id(),settings.rating(),eval?1:settings.moves(),settings.threads()).result();
  if(engine.tiny())return tiny.search(board,engine.id(),Math.max(50,Math.round(settings.seconds()*1000)));
  return stockfish.search(c,board,settings,eval,update,engine.id());
 }
 PhoneEngine.Result recommend(Context c,ChessPosition board,PhoneSettings settings,BooleanSupplier current,PhoneEngine.Update update)throws Exception{
  cancelled=false;String id=EngineCatalog.get(settings.engine()).id();
  PhoneEngine.Result root=one(c,board,settings,id,false,update);if(cancelled||!current.getAsBoolean())throw new CancellationException();
  if(update!=null)update.result(root);
  if(!settings.predict()||settings.predictionPlies()<2||root.lines().isEmpty())return root;
  PhoneEngine.Line first=root.lines().get(0);List<String> pv=new ArrayList<>();ChessPosition next=board;
  for(String move:first.pv()){if(pv.size()>=settings.predictionPlies()||!next.legal().contains(move))break;pv.add(move);next=next.play(move);}
  long until=System.nanoTime()+(long)(settings.predictionSeconds()*1000000000L);
  while(pv.size()<settings.predictionPlies()&&!next.legal().isEmpty()&&System.nanoTime()<until){
   if(cancelled||!current.getAsBoolean())throw new CancellationException();PhoneEngine.Result reply;
   try{reply=one(c,next,settings,id,false,null);}catch(CancellationException cancelledSearch){throw cancelledSearch;}catch(Exception optionalPredictionFailed){break;}
   if(reply.lines().isEmpty())break;String move=reply.lines().get(0).move();if(!next.legal().contains(move))throw new java.io.IOException("Engine returned an illegal continuation");pv.add(move);next=next.play(move);
   List<PhoneEngine.Line> intermediate=new ArrayList<>(root.lines());intermediate.set(0,new PhoneEngine.Line(first.move(),first.cp(),first.mate(),first.depth(),new ArrayList<>(pv)));if(update!=null)update.result(new PhoneEngine.Result(root.fen(),root.provider(),intermediate));
  }
  List<PhoneEngine.Line> lines=new ArrayList<>(root.lines());lines.set(0,new PhoneEngine.Line(first.move(),first.cp(),first.mate(),first.depth(),pv));return new PhoneEngine.Result(root.fen(),root.provider(),lines);
 }
 Evaluated evaluate(Context c,ChessPosition board,PhoneSettings settings)throws Exception{
  cancelled=false;String id=EngineCatalog.get(settings.evaluator()).id();EngineCatalog.Entry engine=EngineCatalog.get(id);
  if(engine.maia()){
   MaiaLocal.Prediction prediction=maia.search(c,board,id,settings.rating(),1,settings.threads());return new Evaluated(engine.name()+" · human expected score "+String.format(Locale.ROOT,"%.2f",prediction.whiteExpected()),prediction.whiteExpected());
  }
  PhoneEngine.Result result=one(c,board,settings,id,true,null);if(result.lines().isEmpty())return new Evaluated("No evaluation",.5f);PhoneEngine.Line lead=result.lines().get(0);
  String score=lead.mate()!=null?"Mate "+lead.mate():lead.cp()!=null?String.format(Locale.ROOT,"%+.2f",lead.cp()/100.):"—";
  float share=lead.mate()!=null?(lead.mate()>0?1:0):lead.cp()!=null?(float)(1/(1+Math.exp(-lead.cp()/250.))):.5f;
  return new Evaluated(engine.name()+" · "+score+" · White’s perspective",share);
 }
 void cancel(){cancelled=true;stockfish.cancel();maia.cancel();tiny.cancel();}
 public void close(){cancel();stockfish.close();maia.close();tiny.close();}
}
