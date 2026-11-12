package app.boardlens.companion;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.CancellationException;
import org.json.JSONObject;

/** Calls the original statically compiled C# bots inside this Android process. */
final class TinyLocal implements AutoCloseable {
 private Object bridge;private Method search,cancel,release;
 static boolean available(){try{Class.forName("app.boardlens.companion.TinyRuntime",false,TinyLocal.class.getClassLoader());return true;}catch(ClassNotFoundException absent){return false;}}
 private void init()throws Exception{if(bridge!=null)return;Class<?> type=Class.forName("app.boardlens.companion.TinyRuntime");bridge=type.getConstructor().newInstance();search=type.getMethod("search",int.class,String.class,int.class);cancel=type.getMethod("cancel");release=type.getMethod("release");}
 PhoneEngine.Result search(ChessPosition board,String engine,int milliseconds)throws Exception{
  init();String value;
  try{value=(String)search.invoke(bridge,Integer.parseInt(engine.substring(4)),board.fen(),milliseconds);}
  catch(InvocationTargetException error){throw new java.io.IOException(error.getCause()==null?error.getMessage():error.getCause().getMessage());}
  if(value==null||value.isEmpty())return new PhoneEngine.Result(board.fen(),engine,Collections.emptyList());
  JSONObject reply=new JSONObject(value);if(reply.optBoolean("cancelled"))throw new CancellationException();if(reply.has("error"))throw new java.io.IOException(reply.getString("error"));String move=reply.getString("move");if(!board.legal().contains(move))throw new java.io.IOException("Tiny bot returned an illegal move");
  return new PhoneEngine.Result(board.fen(),engine,java.util.Arrays.asList(new PhoneEngine.Line(move,null,null,0,java.util.Arrays.asList(move))));
 }
 void cancel(){try{if(bridge!=null)cancel.invoke(bridge);}catch(Exception ignored){}}
 public void close(){cancel();try{if(bridge!=null)release.invoke(bridge);}catch(Exception ignored){}bridge=null;search=null;cancel=null;release=null;}
}
