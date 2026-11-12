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
 private volatile OrtSession.RunOptions active;
 private volatile boolean cancelled;
 private void load(Context c,String id,int requestedThreads)throws Exception{
  if(session!=null&&loaded.equals(id)&&threads==requestedThreads)return;
  if(session!=null)session.close();session=null;
  if(!PhoneModels.ready(c,id))throw new java.io.IOException("Download "+EngineCatalog.get(id).name()+" in Models first");
  try(OrtSession.SessionOptions options=new OrtSession.SessionOptions()){
   options.setIntraOpNumThreads(requestedThreads);options.setInterOpNumThreads(1);
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
  cancelled=false;load(c,id,requestedThreads);if(cancelled)throw new CancellationException();boolean two=id.equals("maia2");
  float[] data=MaiaEncoding.board(board,two);long elo=two?MaiaEncoding.ratingBucket(rating):rating;
  try(OnnxTensor input=OnnxTensor.createTensor(env,FloatBuffer.wrap(data),two?new long[]{1,18,8,8}:new long[]{1,64,97});
      OnnxTensor self=OnnxTensor.createTensor(env,LongBuffer.wrap(new long[]{elo}),new long[]{1});
      OnnxTensor opponent=OnnxTensor.createTensor(env,LongBuffer.wrap(new long[]{elo}),new long[]{1});
      OrtSession.RunOptions options=new OrtSession.RunOptions()){
   active=options;if(cancelled)options.setTerminate(true);
   Map<String,OnnxTensor> inputs=new HashMap<>();inputs.put("board",input);inputs.put("self_rating",self);inputs.put("opponent_rating",opponent);
   try(OrtSession.Result output=session.run(inputs,options)){
    if(cancelled)throw new CancellationException();float[] policy=((float[][])output.get(0).getValue())[0];float[] value=((float[][])output.get(1).getValue())[0];
    List<String> legal=board.legal();for(String move:legal)if(!vocabulary.containsKey(MaiaEncoding.canonicalMove(move,board.white)))throw new java.io.IOException("Move vocabulary mismatch");
    legal.sort((a,b)->Float.compare(policy[vocabulary.get(MaiaEncoding.canonicalMove(b,board.white))],policy[vocabulary.get(MaiaEncoding.canonicalMove(a,board.white))]));
    List<PhoneEngine.Line> lines=new ArrayList<>();for(String move:legal.subList(0,Math.min(count,legal.size())))lines.add(new PhoneEngine.Line(move,null,null,1,java.util.Arrays.asList(move)));
    float expected;
    if(two)expected=Math.max(0,Math.min(1,value[0]/2+.5f));
    else{double max=Math.max(value[0],Math.max(value[1],value[2])),loss=Math.exp(value[0]-max),draw=Math.exp(value[1]-max),win=Math.exp(value[2]-max);expected=(float)((win+.5*draw)/(loss+draw+win));}
    if(!board.white)expected=1-expected;
    return new Prediction(new PhoneEngine.Result(board.fen(),EngineCatalog.get(id).name(),lines),expected);
   }finally{active=null;}
  }
 }
 void cancel(){cancelled=true;OrtSession.RunOptions options=active;if(options!=null)try{options.setTerminate(true);}catch(OrtException ignored){}}
 public void close(){cancel();try{if(session!=null)session.close();}catch(OrtException ignored){}session=null;}
}
