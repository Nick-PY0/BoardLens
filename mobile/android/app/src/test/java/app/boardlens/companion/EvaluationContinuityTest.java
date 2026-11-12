package app.boardlens.companion;
import android.app.Application;
import android.graphics.Rect;
import android.os.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import java.lang.reflect.*;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
public class EvaluationContinuityTest {
 private void set(Object target,String name,Object value)throws Exception{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);f.set(target,value);}
 @Test public void pendingRefreshAndTurningEvaluationOffNeverResetLastFill()throws Exception{
  var controller=Robolectric.buildService(ScreenService.class).create();ScreenService service=controller.get();PhoneSettings settings=new PhoneSettings(service);settings.p.edit().clear().putString("engine","maia2").putBoolean("evaluation_enabled",false).commit();set(service,"settings",settings);ScreenService.whiteShare=.82f;ScreenService.hasEvaluationValue=true;
  try{
   Method analyze=ScreenService.class.getDeclaredMethod("analyze",ChessPosition.class,Rect.class,boolean.class);analyze.setAccessible(true);analyze.invoke(service,new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),new Rect(0,100,512,612),true);
   assertEquals(.82f,ScreenService.whiteShare,.0001);assertTrue(ScreenService.hasEvaluationValue);assertEquals("Evaluation off",ScreenService.evaluation);
   Method key=ScreenService.class.getDeclaredMethod("settingsKey");key.setAccessible(true);String before=(String)key.invoke(service);settings.p.edit().putBoolean("arrows",false).putBoolean("screen_evaluation",false).putString("evaluation_position","Top").commit();assertEquals(before,key.invoke(service));settings.p.edit().putFloat("seconds",2).commit();assertNotEquals(before,key.invoke(service));
  }finally{controller.destroy();Shadows.shadowOf(Looper.getMainLooper()).idle();ScreenService.hasEvaluationValue=false;ScreenService.whiteShare=.5f;}
 }
}
