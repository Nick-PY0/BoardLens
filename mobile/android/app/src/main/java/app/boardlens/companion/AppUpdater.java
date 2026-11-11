package app.boardlens.companion;

import android.app.*;
import android.content.*;
import android.content.pm.*;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.widget.Toast;
import java.io.*;
import java.net.*;
import java.security.MessageDigest;
import java.util.*;
import org.json.*;

/** User-requested updates pinned to this project's GitHub release assets. */
public final class AppUpdater {
    private static final String REPO="Nick-PY0/BoardLens", ASSET="BoardLens-Companion-Android.apk";
    private final Activity activity;
    private boolean busy=false;
    private File pending;
    public AppUpdater(Activity activity){this.activity=activity;}
    private void ui(Runnable action){activity.runOnUiThread(()->{if(!activity.isFinishing()&&!activity.isDestroyed())action.run();});}
    private void notice(String text){ui(()->new AlertDialog.Builder(activity).setTitle("BoardLens updates").setMessage(text).setPositiveButton("OK",null).show());}
    private static String hex(byte[] value){StringBuilder out=new StringBuilder();for(byte b:value)out.append(String.format(Locale.ROOT,"%02x",b&255));return out.toString();}
    private static byte[] read(String address,int maximum)throws Exception{
        HttpURLConnection connection=(HttpURLConnection)new URL(address).openConnection();connection.setConnectTimeout(12000);connection.setReadTimeout(15000);connection.setRequestProperty("User-Agent","BoardLens-Android");connection.setRequestProperty("Accept","application/vnd.github+json");
        try(InputStream input=connection.getInputStream();ByteArrayOutputStream output=new ByteArrayOutputStream()){
            byte[] buffer=new byte[8192];int count,total=0;while((count=input.read(buffer))!=-1){total+=count;if(total>maximum)throw new IOException("Update response is too large.");output.write(buffer,0,count);}return output.toByteArray();
        }finally{connection.disconnect();}
    }
    private static String assetUrl(JSONObject asset)throws Exception{
        String value=asset.getString("browser_download_url");URI uri=new URI(value);
        if(!"https".equals(uri.getScheme())||!"github.com".equals(uri.getHost())||uri.getUserInfo()!=null||uri.getQuery()!=null||uri.getFragment()!=null||!uri.getPath().startsWith("/"+REPO+"/releases/download/"))throw new IOException("Unexpected update URL.");return value;
    }
    private long version(PackageInfo info){return Build.VERSION.SDK_INT>=28?info.getLongVersionCode():info.versionCode;}
    public void check(){
        if(busy)return;busy=true;
        ProgressDialog progress=new ProgressDialog(activity);progress.setMessage("Checking GitHub…");progress.setCancelable(false);progress.show();
        new Thread(()->{
            try{
                JSONObject release=new JSONObject(new String(read("https://api.github.com/repos/"+REPO+"/releases/latest",2000000),java.nio.charset.StandardCharsets.UTF_8));
                if(release.optBoolean("draft")||release.optBoolean("prerelease"))throw new IOException("No stable release is available.");
                Map<String,JSONObject> assets=new HashMap<>();JSONArray list=release.getJSONArray("assets");for(int i=0;i<list.length();i++){JSONObject item=list.getJSONObject(i);assets.put(item.getString("name"),item);}
                if(!assets.containsKey("boardlens-update.json")||!assets.containsKey(ASSET))throw new IOException("This release is missing its update files.");
                JSONObject manifest=new JSONObject(new String(read(assetUrl(assets.get("boardlens-update.json")),65536),java.nio.charset.StandardCharsets.UTF_8));
                if(manifest.getInt("schema")!=1)throw new IOException("Unsupported update manifest.");
                JSONObject info=manifest.getJSONObject("android");String hash=info.getString("sha256"),url=assetUrl(assets.get(ASSET));
                if(!ASSET.equals(info.getString("asset"))||!hash.matches("[a-f0-9]{64}"))throw new IOException("The Android update is incomplete.");
                long installed=version(activity.getPackageManager().getPackageInfo(activity.getPackageName(),0));
                if(info.getLong("version_code")<=installed){ui(()->{progress.dismiss();busy=false;notice("You have the latest version.");});return;}
                String name=info.getString("version");long expected=info.getLong("version_code");
                ui(()->{progress.dismiss();busy=false;new AlertDialog.Builder(activity).setTitle("Update to "+name+"?").setMessage("Download from BoardLens on GitHub. Android will ask you to confirm installation. Your connection settings stay saved.").setNegativeButton("Later",null).setPositiveButton("Download",(dialog,which)->download(url,hash,expected)).show();});
            }catch(Exception error){ui(()->{progress.dismiss();busy=false;notice("Could not check for updates. Check your connection or try again after the first release is published.\n\n"+error.getMessage());});}
        },"BoardLens-update-check").start();
    }
    private Set<String> certificates(PackageInfo info)throws Exception{
        android.content.pm.Signature[] signatures=Build.VERSION.SDK_INT>=28?info.signingInfo.getApkContentsSigners():info.signatures;
        Set<String> hashes=new HashSet<>();for(android.content.pm.Signature signature:signatures)hashes.add(hex(MessageDigest.getInstance("SHA-256").digest(signature.toByteArray())));return hashes;
    }
    private void download(String address,String expectedHash,long expectedCode){
        if(busy)return;busy=true;ProgressDialog progress=new ProgressDialog(activity);progress.setMessage("Downloading and verifying update…");progress.setCancelable(false);progress.show();
        new Thread(()->{
            File partial=new File(activity.getCacheDir(),"update-download.apk");
            try{
                HttpURLConnection connection=(HttpURLConnection)new URL(address).openConnection();connection.setConnectTimeout(12000);connection.setReadTimeout(20000);connection.setRequestProperty("User-Agent","BoardLens-Android");
                MessageDigest hash=MessageDigest.getInstance("SHA-256");long size=0;
                try(InputStream input=connection.getInputStream();FileOutputStream output=new FileOutputStream(partial)){
                    byte[] buffer=new byte[65536];int count;while((count=input.read(buffer))!=-1){size+=count;if(size>100*1024*1024)throw new IOException("Update is too large.");hash.update(buffer,0,count);output.write(buffer,0,count);}
                }finally{connection.disconnect();}
                if(!expectedHash.equals(hex(hash.digest())))throw new IOException("Checksum mismatch. Nothing was installed.");
                int flags=Build.VERSION.SDK_INT>=28?PackageManager.GET_SIGNING_CERTIFICATES:PackageManager.GET_SIGNATURES;
                PackageInfo next=activity.getPackageManager().getPackageArchiveInfo(partial.getAbsolutePath(),flags),current=activity.getPackageManager().getPackageInfo(activity.getPackageName(),flags);
                if(next==null||!activity.getPackageName().equals(next.packageName)||version(next)!=expectedCode||version(next)<=version(current)||!certificates(next).equals(certificates(current)))throw new IOException("Package identity, version or signing certificate did not match.");
                File verified=new File(activity.getCacheDir(),"update.apk");if(verified.exists()&&!verified.delete())throw new IOException("Could not replace the old update.");if(!partial.renameTo(verified))throw new IOException("Could not save update.");pending=verified;
                ui(()->{progress.dismiss();busy=false;installPending();});
            }catch(Exception error){partial.delete();ui(()->{progress.dismiss();busy=false;notice("Update failed. The installed app is unchanged.\n\n"+error.getMessage());});}
        },"BoardLens-update-download").start();
    }
    public void installPending(){
        if(pending==null||!pending.isFile())return;
        if(!activity.getPackageManager().canRequestPackageInstalls()){
            new AlertDialog.Builder(activity).setTitle("Allow this update").setMessage("Android needs permission for BoardLens to open its downloaded APK. Enable Allow from this source, then return to BoardLens.").setNegativeButton("Later",null).setPositiveButton("Open Android settings",(dialog,which)->activity.startActivityForResult(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:"+activity.getPackageName())),201)).show();return;
        }
        Intent install=new Intent(Intent.ACTION_VIEW);install.setDataAndType(Uri.parse("content://"+activity.getPackageName()+".updates/package.apk"),"application/vnd.android.package-archive");install.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);activity.startActivity(install);
    }
}
