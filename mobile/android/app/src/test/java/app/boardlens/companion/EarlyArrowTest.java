package app.boardlens.companion;

import android.app.Application;
import android.graphics.Rect;
import android.os.Looper;
import java.lang.reflect.*;
import java.util.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
public class EarlyArrowTest {
  private void set(Object target,String name,Object value)throws Exception {Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);f.set(target,value);}
  private Object get(Object target,String name)throws Exception {Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(target);}
  @Test public void onlyMyColorDoesNotSteadyALineWithNoVisibleArrow()throws Exception {
    var controller=Robolectric.buildService(ScreenService.class).create();ScreenService service=controller.get();PhoneSettings prefs=new PhoneSettings(service);
    prefs.p.edit().clear().putBoolean("onlyMine",true).putBoolean("steady",true).apply();
    set(service,"settings",prefs);set(service,"overlay",new ArrowOverlay(service));set(service,"target",new Rect(0,200,512,712));
    ChessPosition board=new ChessPosition("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1");
    Method publish=ScreenService.class.getDeclaredMethod("publishMoves",PhoneEngine.Result.class,ChessPosition.class,Rect.class,boolean.class,long.class,boolean.class);publish.setAccessible(true);
    ScreenService.running=true;ScreenService.phoneVisible=true;
    try {
      String[][] lines={{"e7e5"},{"c7c5","g1f3"},{"g8f6","b1c3"}};
      for(int i=0;i<lines.length;i++){
        var line=new PhoneEngine.Line(lines[i][0],0,null,i+1,Arrays.asList(lines[i]));var result=new PhoneEngine.Result(board.fen(),"Stockfish",Collections.singletonList(line));
        publish.invoke(service,result,board,new Rect(0,200,512,712),true,0L,false);
        assertEquals(i==0?Collections.emptyList():Collections.singletonList("g1f3"),get(service,"lastArrows"));
      }
      var finalLine=new PhoneEngine.Line("g8f6",0,null,18,Arrays.asList("g8f6","b1c3"));
      publish.invoke(service,new PhoneEngine.Result(board.fen(),"Stockfish",Collections.singletonList(finalLine)),board,new Rect(0,200,512,712),true,0L,true);
      assertEquals(Collections.singletonList("b1c3"),get(service,"lastArrows"));
    } finally {controller.destroy();Shadows.shadowOf(Looper.getMainLooper()).idle();ScreenService.phoneVisible=false;}
  }
}
