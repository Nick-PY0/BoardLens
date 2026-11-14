package app.boardlens.companion;
import android.app.*;
import android.content.*;
import android.net.Uri;
import android.view.Gravity;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/** Bounded, cancellable update checks with visible progress and cached manifests. */
public final class AppUpdater implements AutoCloseable {
 private static final String ROOT="https://github.com/Nick-PY0/BoardLens/releases";
 interface Fetch { String read(String url,int max)throws Exception;default void cancel(){} }
 private static final class HttpFetch implements Fetch {
  private final Set<HttpURLConnection> connections=ConcurrentHashMap.newKeySet();
  public String read(String url,int max)throws Exception {
   HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();connections.add(c);c.setConnectTimeout(5000);c.setReadTimeout(5000);c.setRequestProperty("User-Agent","BoardLens-Android");
   try(InputStream in=c.getInputStream()){return new String(Streams.read(in,max),StandardCharsets.UTF_8);}finally{connections.remove(c);c.disconnect();}
  }
  public void cancel(){for(HttpURLConnection c:connections)c.disconnect();}
 }
 private static final class Job {volatile boolean cancelled,manual;volatile String stage="Connecting to GitHub…";ExecutorService workers;Thread thread;}
 private record Release(long code,String version,String apk,String page){}
 private final Activity activity;private final Fetch fetch;private final long timeoutMillis;private Job active;private AlertDialog progress;
 AppUpdater(Activity a){this(a,new HttpFetch());}AppUpdater(Activity a,Fetch fetch){this(a,fetch,15000);}AppUpdater(Activity a,Fetch fetch,long timeoutMillis){activity=a;this.fetch=fetch;this.timeoutMillis=timeoutMillis;}
 public void check(){check(false);}
 static JSONObject assetInfo(JSONObject r,String name){JSONArray list=r.optJSONArray("assets");if(list!=null)for(int i=0;i<list.length();i++){JSONObject a=list.optJSONObject(i);if(a!=null&&name.equals(a.optString("name")))return a;}return new JSONObject();}
 static String asset(JSONObject r,String name){String url=assetInfo(r,name).optString("browser_download_url");return url.startsWith(ROOT+"/download/")?url:"";}
 static boolean eligible(JSONObject r){return !r.optBoolean("draft")&&!r.optBoolean("prerelease")&&!asset(r,"BoardLens-Companion-Android.apk").isEmpty()&&!asset(r,"boardlens-update.json").isEmpty()&&r.optString("html_url").startsWith(ROOT+"/tag/");}
 private boolean usable(){return !activity.isFinishing()&&!activity.isDestroyed();}
 private void stage(Job job,String text){job.stage=text;activity.runOnUiThread(()->{if(active==job&&progress!=null&&progress.isShowing())progress.setMessage(text);});}
 private void showProgress(Job job){
  if(!usable()||progress!=null&&progress.isShowing())return;LinearLayout body=new LinearLayout(activity);body.setGravity(Gravity.CENTER);body.setPadding(0,20,0,20);body.addView(new ProgressBar(activity));
  progress=new AlertDialog.Builder(activity).setTitle("Checking for updates").setMessage(job.stage).setView(body).setNegativeButton("Cancel",(d,w)->cancel(job)).create();progress.setOnCancelListener(d->cancel(job));progress.show();
 }
 private void cancel(Job job){if(active!=job)return;job.cancelled=true;active=null;fetch.cancel();if(job.thread!=null)job.thread.interrupt();if(job.workers!=null)job.workers.shutdownNow();if(progress!=null){progress.dismiss();progress=null;}}
 public void check(boolean quiet){
  if(active!=null){if(!quiet){active.manual=true;showProgress(active);}return;}SharedPreferences prefs=activity.getSharedPreferences("app-updates",0);long now=System.currentTimeMillis();
  if(quiet&&(now-prefs.getLong("lastCheck",0)<6*60*60*1000||now-prefs.getLong("lastAttempt",0)<60000))return;
  Job job=new Job();job.manual=!quiet;active=job;prefs.edit().putLong("lastAttempt",now).apply();if(!quiet)showProgress(job);job.thread=new Thread(()->run(job,prefs,quiet),"BoardLens-update-check");job.thread.start();
 }
 private void run(Job job,SharedPreferences prefs,boolean quiet){
  String message;Release best=null;boolean failed=false;
  try{
   long current=android.os.Build.VERSION.SDK_INT>=28?activity.getPackageManager().getPackageInfo(activity.getPackageName(),0).getLongVersionCode():activity.getPackageManager().getPackageInfo(activity.getPackageName(),0).versionCode;
   JSONArray releases=new JSONArray(fetch.read("https://api.github.com/repos/Nick-PY0/BoardLens/releases?per_page=20",2000000));List<JSONObject> candidates=new ArrayList<>();for(int i=0;i<releases.length()&&candidates.size()<5;i++){JSONObject r=releases.getJSONObject(i);if(eligible(r))candidates.add(r);}
   if(job.cancelled)return;stage(job,"Checking Android releases · 0/"+candidates.size());job.workers=Executors.newFixedThreadPool(3);CompletionService<Release> checks=new ExecutorCompletionService<>(job.workers);
   for(JSONObject release:candidates)checks.submit(()->{
    if(job.cancelled)throw new CancellationException();String url=asset(release,"boardlens-update.json");JSONObject info=assetInfo(release,"boardlens-update.json");String key="manifest:"+url+":"+info.optString("updated_at")+":"+info.optString("digest");String cached=prefs.getString(key,"");String json=cached.isEmpty()?fetch.read(url,65536):cached;JSONObject android=new JSONObject(json).getJSONObject("android");
    if(!android.optString("asset").equals("BoardLens-Companion-Android.apk")||!android.optString("sha256").matches("[a-fA-F0-9]{64}"))throw new IOException("Invalid update manifest");if(cached.isEmpty()&&!job.cancelled)prefs.edit().putString(key,json).apply();return new Release(android.getLong("version_code"),android.optString("version"),asset(release,"BoardLens-Companion-Android.apk"),release.getString("html_url"));
   });
   long until=System.nanoTime()+TimeUnit.MILLISECONDS.toNanos(timeoutMillis);int inspected=0;
   for(int done=0;done<candidates.size();done++){long remaining=until-System.nanoTime();Future<Release> result=remaining>0?checks.poll(remaining,TimeUnit.NANOSECONDS):null;if(result==null)throw new SocketTimeoutException();try{Release r=result.get();inspected++;if(best==null||r.code()>best.code())best=r;}catch(ExecutionException badRelease){}stage(job,"Checking Android releases · "+(done+1)+"/"+candidates.size());}
   if(inspected==0&&!candidates.isEmpty())throw new IOException("Release details unavailable");
   if(best!=null&&best.code()>current)message="Android "+best.version()+" is ready. Download the APK, then approve installation in Android.";else{best=null;message=candidates.isEmpty()?"No Android release is available yet.":"You have the latest Android version.";}if(!job.cancelled)prefs.edit().putLong("lastCheck",System.currentTimeMillis()).apply();
  }catch(Exception error){if(job.cancelled)return;failed=true;best=null;message=error instanceof SocketTimeoutException?"GitHub took too long to respond. Check your connection and try again.":"Could not finish the update check. Check your connection and try again.";}
  finally{if(job.workers!=null)job.workers.shutdownNow();}
  String text=message;Release update=best;boolean error=failed;
  activity.runOnUiThread(()->{if(active!=job)return;active=null;if(progress!=null){progress.dismiss();progress=null;}if(!usable()||!job.manual&&(update==null||!activity.hasWindowFocus()))return;AlertDialog.Builder dialog=new AlertDialog.Builder(activity).setTitle(error?"Update check incomplete":"BoardLens updates").setMessage(text).setNegativeButton("Close",null);if(update!=null){dialog.setPositiveButton("Download APK",(d,w)->activity.startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(update.apk()))));dialog.setNeutralButton("Release notes",(d,w)->activity.startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(update.page()))));}dialog.show();});
 }
 public void close(){if(active!=null)cancel(active);}
}
