package app.boardlens.companion;
import android.app.Application;import android.graphics.Rect;import android.os.*;import org.junit.*;import org.junit.runner.RunWith;import org.robolectric.*;import org.robolectric.annotation.*;import java.nio.file.*;import java.lang.reflect.*;import static org.junit.Assert.*;
/** Regression: an idle captured board must re-analyze even while our own UI is visible. */
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class) @android.annotation.TargetApi(35)
public class MaiaServiceTest {
 private void set(Object target,String field,Object value)throws Exception{Field f=target.getClass().getDeclaredField(field);f.setAccessible(true);f.set(target,value);}
 @Test public void selectingAndFinishingMaiaDownloadRestartsTheIdleBoard()throws Exception{
  String models=System.getenv("BOARDLENS_MAIA_TEST_MODELS");Assume.assumeTrue(models!=null);var controller=Robolectric.buildService(ScreenService.class).create();ScreenService service=controller.get();PhoneSettings prefs=new PhoneSettings(service);prefs.p.edit().clear().putString("engine","maia3-5m").putBoolean("evaluation_enabled",false).putBoolean("predict",false).apply();
  set(service,"settings",prefs);set(service,"capture",new Handler(Looper.getMainLooper()));set(service,"overlay",new ArrowOverlay(service));set(service,"position",new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"));set(service,"target",new Rect(0,100,512,612));ScreenService.running=true;ScreenService.phoneVisible=true;
  try{
   service.getSharedPreferences("phone-model-files",0).edit().remove("maia3-5m").commit();service.applyCurrentSettings();assertTrue(ScreenService.suggestion.startsWith("Download Maia"));
   Path target=PhoneModels.file(service,"maia3-5m").toPath();Files.deleteIfExists(target);Files.createLink(target,Path.of(models,"maia3-5m.onnx"));service.getSharedPreferences("phone-model-files",0).edit().putString("maia3-5m",PhoneModels.entry(service,"maia3-5m").getString("sha256")).commit();service.modelReady("maia3-5m");Shadows.shadowOf(Looper.getMainLooper()).idle();
   long until=System.currentTimeMillis()+10000;while(!ScreenService.suggestion.startsWith("1.")&&System.currentTimeMillis()<until){Thread.sleep(20);Shadows.shadowOf(Looper.getMainLooper()).idle();}
   assertTrue(ScreenService.suggestion,ScreenService.suggestion.startsWith("1."));assertTrue(ScreenService.phoneVisible);assertEquals("Evaluation off",ScreenService.evaluation);
  }finally{controller.destroy();Shadows.shadowOf(Looper.getMainLooper()).idle();ScreenService.phoneVisible=false;}
 }
}
