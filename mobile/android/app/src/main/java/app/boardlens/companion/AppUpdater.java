package app.boardlens.companion;

import android.app.*;
import android.content.*;
import android.net.Uri;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;

/** Checks Android releases independently from desktop. Android handles installation. */
public final class AppUpdater {
 private final Activity activity;private boolean busy;
 private static final String ROOT="https://github.com/Nick-PY0/BoardLens/releases";
 AppUpdater(Activity a){activity=a;}
 public void check(){check(false);}
 static String asset(JSONObject release,String name){JSONArray assets=release.optJSONArray("assets");if(assets!=null)for(int i=0;i<assets.length();i++){JSONObject a=assets.optJSONObject(i);if(a!=null&&name.equals(a.optString("name"))){String url=a.optString("browser_download_url");if(url.startsWith(ROOT+"/download/"))return url;}}return "";}
 static boolean eligible(JSONObject release){return !release.optBoolean("draft")&&!release.optBoolean("prerelease")&&!asset(release,"BoardLens-Companion-Android.apk").isEmpty()&&!asset(release,"boardlens-update.json").isEmpty()&&release.optString("html_url").startsWith(ROOT+"/tag/");}
 private static String read(String url,int max)throws Exception{HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();c.setConnectTimeout(10000);c.setReadTimeout(10000);c.setRequestProperty("User-Agent","BoardLens-Android");try(InputStream in=c.getInputStream()){byte[] data=Streams.read(in,max);if(data.length>max)throw new IOException("Response too large");return new String(data,StandardCharsets.UTF_8);}finally{c.disconnect();}}
 public void check(boolean quiet){
  android.content.SharedPreferences prefs=activity.getSharedPreferences("app-updates",0);long now=System.currentTimeMillis();
  if(busy||quiet&&now-prefs.getLong("lastCheck",0)<6*60*60*1000)return;
  prefs.edit().putLong("lastCheck",now).apply();busy=true;
  new Thread(()->{String message,releaseUrl="";boolean available=false;
   try{
    long current=(android.os.Build.VERSION.SDK_INT>=28?activity.getPackageManager().getPackageInfo(activity.getPackageName(),0).getLongVersionCode():activity.getPackageManager().getPackageInfo(activity.getPackageName(),0).versionCode),next=current;
    JSONArray releases=new JSONArray(read("https://api.github.com/repos/Nick-PY0/BoardLens/releases?per_page=20",2000000));int inspected=0;
    for(int i=0;i<releases.length()&&inspected<5;i++){JSONObject release=releases.getJSONObject(i);if(!eligible(release))continue;inspected++;
     try{JSONObject android=new JSONObject(read(asset(release,"boardlens-update.json"),65536)).getJSONObject("android");long code=android.getLong("version_code");if(code>next&&android.optString("asset").equals("BoardLens-Companion-Android.apk")&&android.optString("sha256").matches("[a-fA-F0-9]{64}")){next=code;releaseUrl=release.getString("html_url");}}catch(Exception invalidManifest){/* A bad or unavailable older release must not hide a valid newer one. */}
    }
    available=next>current;message=available?"A new Android version is ready. Open the release to download it. Android asks before installing; your settings are kept.":inspected>0?"You have the latest Android version.":"No Android release is available yet. Try again later.";
   }catch(Exception error){message="Could not check for updates. Check your connection and try again.";}
   String text=message,url=releaseUrl;boolean update=available;
   activity.runOnUiThread(()->{busy=false;if(activity.isFinishing()||activity.isDestroyed()||quiet&&!update)return;AlertDialog.Builder dialog=new AlertDialog.Builder(activity).setTitle("BoardLens updates").setMessage(text).setNegativeButton("Close",null);if(update)dialog.setPositiveButton("Open release",(d,w)->activity.startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(url))));dialog.show();});
  },"BoardLens-update-check").start();
 }
}
