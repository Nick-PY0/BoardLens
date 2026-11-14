package app.boardlens.companion;
import android.app.*;import android.content.*;import android.graphics.*;import android.os.*;
import java.lang.reflect.*;import java.util.*;import java.util.concurrent.atomic.AtomicLong;
import org.junit.*;import org.junit.runner.RunWith;import org.robolectric.*;import org.robolectric.annotation.*;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
public class ScannerControlsTest {
 private void set(Object o,String n,Object v)throws Exception{Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);f.set(o,v);}
 private Object get(Object o,String n)throws Exception{Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);return f.get(o);}
 private void invoke(Object o,String n)throws Exception{Method m=o.getClass().getDeclaredMethod(n);m.setAccessible(true);m.invoke(o);}
 @Test public void notificationOffersSeparateImmutableScanAndStopCommands(){
  Notification n=ScreenService.captureNotification(RuntimeEnvironment.getApplication());assertEquals(2,n.actions.length);
  assertEquals("Scan now",n.actions[0].title);assertEquals("REFRESH",Shadows.shadowOf(n.actions[0].actionIntent).getSavedIntent().getAction());
  assertEquals("Stop",n.actions[1].title);assertEquals("STOP",Shadows.shadowOf(n.actions[1].actionIntent).getSavedIntent().getAction());
  assertNotEquals(n.actions[0].actionIntent,n.actions[1].actionIntent);assertTrue(n.actions[0].actionIntent.isImmutable());
 }
 @Test public void refreshKeepsSessionAndStillPixelsButDropsOldTarget()throws Exception{
  var c=Robolectric.buildService(ScreenService.class).create();ScreenService s=c.get();Bitmap frame=Bitmap.createBitmap(200,200,Bitmap.Config.ARGB_8888);
  ChessPosition afterMove=new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1").play("g1f3");
  set(s,"position",afterMove);
  set(s,"capture",new Handler(Looper.getMainLooper()));set(s,"cachedFrame",frame);set(s,"searchedFrame",frame);set(s,"target",new Rect(0,0,200,200));set(s,"baseline",new int[9216]);set(s,"needsRead",false);set(s,"lastArrows",List.of("e2e4"));ScreenService.running=true;
  try{s.onStartCommand(new Intent(s,ScreenService.class).setAction("REFRESH"),0,1);Shadows.shadowOf(Looper.getMainLooper()).idle();
   assertTrue(ScreenService.running);assertNull(get(s,"target"));assertSame(frame,get(s,"cachedFrame"));assertFalse(frame.isRecycled());assertNull(get(s,"searchedFrame"));assertEquals(List.of(),get(s,"lastArrows"));assertTrue((Boolean)get(s,"needsRead"));
   ChessPosition retained=(ChessPosition)get(s,"position");assertNotNull("A rescan must retain the last confirmed chess state",retained);
   ChessPosition same=ChessPosition.sync(retained,afterMove.placement(),"Auto");assertEquals(afterMove.fen(),same.fen());assertFalse("Scan now must not change Black's turn to White",same.white);
   ChessPosition reply=afterMove.play("g8f6");assertEquals(reply.fen(),ChessPosition.sync(retained,reply.placement(),"Auto").fen());
  }finally{c.destroy();Shadows.shadowOf(Looper.getMainLooper()).idle();}
 }
 @Test public void lostBoardRejectsLateSearchResultsAndForcesNewAnalysis()throws Exception{
  var c=Robolectric.buildService(ScreenService.class).create();ScreenService s=c.get();PhoneSettings prefs=new PhoneSettings(s);prefs.p.edit().clear().putBoolean("evaluation_enabled",false).commit();
  set(s,"settings",prefs);set(s,"overlay",new ArrowOverlay(s));set(s,"target",new Rect(0,100,512,612));set(s,"baseline",new int[9216]);set(s,"lastAnalyzedSettings","old search");set(s,"lastArrows",List.of("e2e4"));ScreenService.running=true;
  try{
   AtomicLong generation=(AtomicLong)get(s,"generation");long old=generation.get();invoke(s,"loseTarget");assertTrue(generation.get()>old);assertEquals("",get(s,"lastAnalyzedSettings"));
   ChessPosition b=new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
   Method m=ScreenService.class.getDeclaredMethod("publishMoves",PhoneEngine.Result.class,ChessPosition.class,Rect.class,boolean.class,long.class,boolean.class);m.setAccessible(true);
   m.invoke(s,new PhoneEngine.Result(b.fen(),"late",List.of(new PhoneEngine.Line("e2e4",0,null,1,List.of("e2e4")))),b,new Rect(0,100,512,612),true,old,true);
   assertEquals(List.of(),get(s,"lastArrows"));assertNull(get(s,"target"));
  }finally{c.destroy();Shadows.shadowOf(Looper.getMainLooper()).idle();}
 }
 @Test public void unconfirmedGeometryCannotDisplayOldArrows()throws Exception{
  var c=Robolectric.buildService(ScreenService.class).create();ScreenService s=c.get();ArrowOverlay overlay=new ArrowOverlay(s);PhoneSettings p=new PhoneSettings(s);p.p.edit().clear().putBoolean("evaluation_enabled",false).commit();
  org.robolectric.shadows.ShadowSettings.setCanDrawOverlays(true);set(s,"settings",p);set(s,"overlay",overlay);set(s,"target",new Rect(0,100,512,612));set(s,"lastArrows",List.of("e2e4"));ScreenService.running=true;ScreenService.phoneVisible=false;
  try{invoke(s,"renderOverlay");Shadows.shadowOf(Looper.getMainLooper()).idle();assertFalse(overlay.hasArrows());
   set(s,"baseline",new int[9216]);set(s,"needsRead",false);invoke(s,"renderOverlay");Shadows.shadowOf(Looper.getMainLooper()).idle();assertTrue(overlay.hasArrows());
  }finally{c.destroy();Shadows.shadowOf(Looper.getMainLooper()).idle();}
 }
}
