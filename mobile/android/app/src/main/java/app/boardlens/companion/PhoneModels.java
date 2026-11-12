package app.boardlens.companion;
import android.content.Context;
import java.io.*;
import java.net.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.function.BooleanSupplier;
import org.json.*;

/** Optional data models; fixed HTTPS sources, exact byte counts and SHA-256. */
final class PhoneModels {
 static JSONObject entry(Context c,String id)throws Exception{try(InputStream in=c.getAssets().open("engines/models.json")){JSONArray all=new JSONObject(new String(Streams.read(in,65536),java.nio.charset.StandardCharsets.UTF_8)).getJSONArray("models");for(int i=0;i<all.length();i++)if(all.getJSONObject(i).getString("id").equals(id))return all.getJSONObject(i);}throw new IOException("Model not in this release");}
 static File file(Context c,String id){File folder=new File(c.getFilesDir(),"phone-models");folder.mkdirs();return new File(folder,id+".onnx");}
 static boolean ready(Context c,String id){try{JSONObject e=entry(c,id);File f=file(c,id);return f.isFile()&&f.length()==e.getLong("bytes")&&c.getSharedPreferences("phone-model-files",0).getString(id,"").equals(e.getString("sha256"));}catch(Exception missing){return false;}}
 static String size(Context c,String id){try{return String.format(Locale.ROOT,"%.0f MB",entry(c,id).getLong("bytes")/1000000.0);}catch(Exception e){return "Optional download";}}
 static synchronized void download(Context c,String id,BooleanSupplier cancelled,EngineFiles.Progress progress)throws Exception{
  if(ready(c,id))return;JSONObject model=entry(c,id);long expected=model.getLong("bytes");String hash=model.getString("sha256"),url=model.getString("url");
  URI uri=new URI(url);if(!uri.getScheme().equals("https")||!uri.getHost().equals("github.com")||!uri.getPath().startsWith("/Nick-PY0/BoardLens/releases/download/"))throw new IOException("Invalid model source");
  File target=file(c,id),partial=new File(target.getPath()+".part");if(target.getParentFile().getUsableSpace()<expected+10000000)throw new IOException("Free space needed: "+size(c,id));
  HttpURLConnection connection=(HttpURLConnection)new URL(url).openConnection();connection.setConnectTimeout(15000);connection.setReadTimeout(20000);connection.setRequestProperty("User-Agent","BoardLens-Android");
  try{MessageDigest sha=MessageDigest.getInstance("SHA-256");long got=0;try(InputStream in=connection.getInputStream();FileOutputStream out=new FileOutputStream(partial)){byte[] bytes=new byte[65536];int n;while((n=in.read(bytes))!=-1){if(cancelled.getAsBoolean())throw new InterruptedIOException("Download cancelled");got+=n;if(got>expected)throw new IOException("Unexpected model size");sha.update(bytes,0,n);out.write(bytes,0,n);progress.update(got,expected);}}
   StringBuilder actual=new StringBuilder();for(byte b:sha.digest())actual.append(String.format(Locale.ROOT,"%02x",b&255));if(got!=expected||!actual.toString().equals(hash))throw new IOException("Model checksum did not match");
   if(!partial.renameTo(target))throw new IOException("Could not save model");c.getSharedPreferences("phone-model-files",0).edit().putString(id,hash).apply();
  }finally{connection.disconnect();partial.delete();}
 }
}
