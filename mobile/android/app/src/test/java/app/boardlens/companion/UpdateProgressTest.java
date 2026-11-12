package app.boardlens.companion;
import android.app.*;
import android.os.Looper;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import org.json.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import org.robolectric.shadows.ShadowAlertDialog;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
public class UpdateProgressTest {
 private static final String ROOT="https://github.com/Nick-PY0/BoardLens/releases";
 private Activity activity;
 @Before public void setup(){activity=Robolectric.buildActivity(Activity.class).setup().get();activity.getSharedPreferences("app-updates",0).edit().clear().commit();}
 private JSONObject release(int code)throws Exception{return new JSONObject().put("html_url",ROOT+"/tag/test"+code).put("assets",new JSONArray()
  .put(new JSONObject().put("name","BoardLens-Companion-Android.apk").put("browser_download_url",ROOT+"/download/test"+code+"/BoardLens-Companion-Android.apk"))
  .put(new JSONObject().put("name","boardlens-update.json").put("updated_at","once").put("browser_download_url",ROOT+"/download/test"+code+"/boardlens-update.json")));}
 private String manifest(int code){return "{\"android\":{\"asset\":\"BoardLens-Companion-Android.apk\",\"version_code\":"+code+",\"version\":\"9."+code+"\",\"sha256\":\""+"a".repeat(64)+"\"}}";}
 private void await(java.util.function.BooleanSupplier done)throws Exception{long until=System.nanoTime()+TimeUnit.SECONDS.toNanos(4);while(!done.getAsBoolean()&&System.nanoTime()<until){Shadows.shadowOf(Looper.getMainLooper()).idle();Thread.sleep(10);}Shadows.shadowOf(Looper.getMainLooper()).idle();assertTrue("Update check must finish",done.getAsBoolean());}
 @Test public void manualCheckAttachesToAutomaticCheckAndCanCancel()throws Exception{
  CountDownLatch started=new CountDownLatch(1),blocked=new CountDownLatch(1);AtomicInteger requests=new AtomicInteger();AtomicBoolean cancelled=new AtomicBoolean();
  AppUpdater updater=new AppUpdater(activity,new AppUpdater.Fetch(){public String read(String u,int max)throws Exception{requests.incrementAndGet();started.countDown();blocked.await();return "[]";}public void cancel(){cancelled.set(true);blocked.countDown();}});
  updater.check(true);assertTrue(started.await(2,TimeUnit.SECONDS));updater.check();AlertDialog progress=ShadowAlertDialog.getLatestAlertDialog();assertTrue(progress.isShowing());assertEquals("Checking for updates",Shadows.shadowOf(progress).getTitle());
  progress.getButton(AlertDialog.BUTTON_NEGATIVE).performClick();Shadows.shadowOf(Looper.getMainLooper()).idle();assertTrue(cancelled.get());assertFalse(progress.isShowing());assertEquals(1,requests.get());updater.close();
 }
 @Test public void newestValidManifestWinsAndCachedManifestsAvoidRepeatDownloads()throws Exception{
  String list=new JSONArray().put(release(90)).put(release(91)).put(release(92)).toString();AtomicInteger manifests=new AtomicInteger();
  AppUpdater updater=new AppUpdater(activity,(url,max)->{if(url.startsWith("https://api.github.com/"))return list;manifests.incrementAndGet();if(url.contains("test91/"))throw new java.io.IOException("old release unavailable");return manifest(url.contains("test92/")?92:90);});
  updater.check();AlertDialog progress=ShadowAlertDialog.getLatestAlertDialog();await(()->ShadowAlertDialog.getLatestAlertDialog()!=progress);
  AlertDialog result=ShadowAlertDialog.getLatestAlertDialog();assertTrue(Shadows.shadowOf(result).getMessage().toString().contains("9.92"));assertEquals(3,manifests.get());result.dismiss();
  updater.check();AlertDialog second=ShadowAlertDialog.getLatestAlertDialog();await(()->ShadowAlertDialog.getLatestAlertDialog()!=second);assertEquals("Only unavailable manifest is retried",4,manifests.get());updater.close();
 }
}
