package app.boardlens.companion;
import ai.onnxruntime.*;
import android.content.Context;
import java.nio.*;
import java.util.*;
import java.util.concurrent.CancellationException;
import org.json.JSONArray;

/** Real official Maia weights evaluated locally through ONNX Runtime. */
final class MaiaLocal implements AutoCloseable {
 record Prediction(PhoneEngine.Result result,float whiteExpected){}
 private final OrtEnvironment env=OrtEnvironment.getEnvironment();
 private OrtSession session;private String loaded="";private int threads;
 private Map<String,Integer> vocabulary;
 private record Key(String model,long rating,int threads,String fen){}
 private record Ranked(List<String> moves,float whiteExpected){}
 // Immutable move rankings also serve future board positions calculated by
 // reply prediction. The small, bounded cache never stores screenshots/tensors.
 private final Map<Key,Ranked> cache=new LinkedHashMap<>(64,.75f,true){
  @Override protected boolean removeEldestEntry(Map.Entry<Key,Ranked> entry){return size()>64;}
 };
 private long inferenceCount,cacheHits;
 private final Object runLock=new Object();
 private volatile OrtSession.RunOptions active;
 private volatile boolean cancelled;
 void prepare(Context c,String id,int requestedThreads)throws Exception{
  cancelled=false;load(c,id,requestedThreads);
 }
 private void load(Context c,String id,int requestedThreads)throws Exception{
  if(session!=null&&loaded.equals(id)&&threads==requestedThreads)return;
  if(session!=null)session.close();session=null;
  if(!PhoneModels.ready(c,id))throw new java.io.IOException("Download "+EngineCatalog.get(id).name()+" in Models first");
  try(OrtSession.SessionOptions options=new OrtSession.SessionOptions()){
   options.setIntraOpNumThreads(requestedThreads);options.setInterOpNumThreads(1);
   options.addConfigEntry("session.intra_op.allow_spinning","0");
   options.addConfigEntry("session.inter_op.allow_spinning","0");
   session=env.createSession(PhoneModels.file(c,id).getAbsolutePath(),options);
  }
  String family=id.equals("maia2")?"maia2":"maia3";vocabulary=new HashMap<>();
  try(var in=c.getAssets().open("engines/"+family+"-moves.json")){
   JSONArray moves=new JSONArray(new String(Streams.read(in,1000000),java.nio.charset.StandardCharsets.UTF_8));
   for(int i=0;i<moves.length();i++)vocabulary.put(moves.getString(i),i);
  }
  loaded=id;threads=requestedThreads;
 }
 Prediction search(Context c,ChessPosition board,String id,int rating,int count,int requestedThreads)throws Exception{
  cancelled=false;boolean two=id.equals("maia2");long elo=two?MaiaEncoding.ratingBucket(rating):rating;
  Key key=new Key(id,elo,requestedThreads,board.fen());Ranked cached=cache.get(key);
  if(cached!=null){cacheHits++;return result(board,id,count,cached);}
  load(c,id,requestedThreads);if(cancelled)throw new CancellationException();
  float[] data=MaiaEncoding.board(board,two);
  try(OnnxTensor input=OnnxTensor.createTensor(env,FloatBuffer.wrap(data),two?new long[]{1,18,8,8}:new long[]{1,64,97});
      OnnxTensor self=OnnxTensor.createTensor(env,LongBuffer.wrap(new long[]{elo}),new long[]{1});
      OnnxTensor opponent=OnnxTensor.createTensor(env,LongBuffer.wrap(new long[]{elo}),new long[]{1})){
   OrtSession.RunOptions options=beginRun();
   try{
   Map<String,OnnxTensor> inputs=new HashMap<>();inputs.put("board",input);inputs.put("self_rating",self);inputs.put("opponent_rating",opponent);
   inferenceCount++;
   try(OrtSession.Result output=session.run(inputs,options)){
    if(cancelled)throw new CancellationException();float[] policy=((float[][])output.get(0).getValue())[0];float[] value=((float[][])output.get(1).getValue())[0];
    List<String> legal=board.legal();for(String move:legal)if(!vocabulary.containsKey(MaiaEncoding.canonicalMove(move,board.white)))throw new java.io.IOException("Move vocabulary mismatch");
    legal.sort((a,b)->Float.compare(policy[vocabulary.get(MaiaEncoding.canonicalMove(b,board.white))],policy[vocabulary.get(MaiaEncoding.canonicalMove(a,board.white))]));
    float expected;
    if(two)expected=Math.max(0,Math.min(1,value[0]/2+.5f));
    else{double max=Math.max(value[0],Math.max(value[1],value[2])),loss=Math.exp(value[0]-max),draw=Math.exp(value[1]-max),win=Math.exp(value[2]-max);expected=(float)((win+.5*draw)/(loss+draw+win));}
    if(!board.white)expected=1-expected;
    if(cancelled)throw new CancellationException();
    Ranked ranking=new Ranked(List.copyOf(legal),expected);cache.put(key,ranking);
    return result(board,id,count,ranking);
   }
   }finally{endRun(options);}
  }
 }
 private Prediction result(ChessPosition board,String id,int count,Ranked ranked){
  List<PhoneEngine.Line> lines=new ArrayList<>();
  for(String move:ranked.moves().subList(0,Math.min(count,ranked.moves().size())))lines.add(new PhoneEngine.Line(move,null,null,1,Collections.singletonList(move)));
  return new Prediction(new PhoneEngine.Result(board.fen(),EngineCatalog.get(id).name(),lines),ranked.whiteExpected());
 }
 private OrtSession.RunOptions beginRun()throws OrtException{
  synchronized(runLock){OrtSession.RunOptions options=new OrtSession.RunOptions();active=options;if(cancelled)options.setTerminate(true);return options;}
 }
 private void endRun(OrtSession.RunOptions options){
  // Cancellation and disposal share ownership of the native RunOptions handle.
  // A cancel request must never keep a pointer after inference closes it.
  synchronized(runLock){if(active==options)active=null;options.close();}
 }
 void cancel(){cancelled=true;synchronized(runLock){if(active!=null)try{active.setTerminate(true);}catch(OrtException ignored){}}}
 public void close(){cancel();try{if(session!=null)session.close();}catch(OrtException ignored){}session=null;cache.clear();}
}
