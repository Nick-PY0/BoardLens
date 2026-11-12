package app.boardlens.companion;

import android.app.Application;
import android.graphics.*;
import android.os.*;
import java.io.*;
import java.lang.reflect.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import static org.junit.Assert.*;

/** A still opening board must finish acquisition without waiting for a move. */
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class BoardAcquisitionTest {
  private static final String START="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR";
  private void set(Object target,String name,Object value)throws Exception {
    Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);f.set(target,value);
  }
  private void tick(ScreenService service)throws Exception {
    Method m=ScreenService.class.getDeclaredMethod("tick");m.setAccessible(true);m.invoke(service);
  }
  @Test public void openingScreenConfirmsWithNoNewCaptureAndRapidPolling()throws Exception {
    var controller=Robolectric.buildService(ScreenService.class).create();
    ScreenService service=controller.get();PhoneSettings prefs=new PhoneSettings(service);
    prefs.p.edit().clear().putBoolean("evaluation_enabled",false).apply();
    Bitmap frame;try(InputStream in=getClass().getClassLoader().getResourceAsStream("fixtures/chesscom-starting-layout-nov10.png")){frame=BitmapFactory.decodeStream(in);}
    set(service,"settings",prefs);set(service,"overlay",new ArrowOverlay(service));
    set(service,"reader",new BoardReader(service));set(service,"cachedFrame",frame);
    set(service,"lastScan",-1000L);
    ScreenService.running=true;ScreenService.phoneVisible=false;ScreenService.fen="";
    long reads=ScreenService.reads;
    try {
      tick(service);assertEquals("Opening board should be found in the first recognition",reads+1,ScreenService.reads);
      SystemClock.sleep(4);tick(service);
      assertEquals("Early ticks must not re-run inference or reset its timer",reads+1,ScreenService.reads);
      SystemClock.sleep(24);tick(service);
      assertTrue(ScreenService.status,ScreenService.fen.startsWith(START+" w KQkq"));
      assertEquals(reads+1,ScreenService.reads);
    } finally {controller.destroy();Shadows.shadowOf(Looper.getMainLooper()).idle();}
  }
  @Test public void initialBoardCropReadsWithoutAnyMove()throws Exception {
    try(BoardReader reader=new BoardReader(RuntimeEnvironment.getApplication());InputStream in=getClass().getClassLoader().getResourceAsStream("fixtures/chesscom-starting-board.png")){
      Bitmap image=BitmapFactory.decodeStream(in);long start=System.nanoTime();BoardReader.Read read=reader.read(image,null,"Auto");
      assertNotNull(reader.diagnostic,read);assertEquals(START,read.placement());assertTrue(read.whiteBottom());
      System.out.println("Static opening board acquisition on host: "+((System.nanoTime()-start)/1000000)+" ms");image.recycle();
    }
  }
  @Test public void stillOpeningBoardIsFoundInPhonePortraitForBothColors()throws Exception {
    try(BoardReader reader=new BoardReader(RuntimeEnvironment.getApplication());InputStream in=getClass().getClassLoader().getResourceAsStream("fixtures/chesscom-starting-board.png")){
      Bitmap board=BitmapFactory.decodeStream(in);
      for(boolean whiteBottom:new boolean[]{true,false}){
        Bitmap phone=Bitmap.createBitmap(720,1520,Bitmap.Config.ARGB_8888);Canvas canvas=new Canvas(phone);canvas.drawColor(0xff262421);Paint paint=new Paint(Paint.FILTER_BITMAP_FLAG);
        for(int row=0;row<8;row++)for(int col=0;col<8;col++){
          int sr=whiteBottom?row:7-row,sc=whiteBottom?col:7-col;
          canvas.drawBitmap(board,new Rect(sc*158,sr*158,(sc+1)*158,(sr+1)*158),new Rect(20+col*85,300+row*85,20+(col+1)*85,300+(row+1)*85),paint);
        }
        BoardReader.Read read=reader.read(phone,null,"Auto");assertNotNull(reader.diagnostic,read);assertEquals(START,read.placement());assertEquals(whiteBottom,read.whiteBottom());phone.recycle();
      }
      board.recycle();
    }
  }
}
