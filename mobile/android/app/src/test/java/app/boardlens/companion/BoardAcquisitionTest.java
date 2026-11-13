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
  @Test public void openingCanConfirmWithAnAnimatedEmptySquareAndNoPieceMove()throws Exception{
    var controller=Robolectric.buildService(ScreenService.class).create();ScreenService service=controller.get();
    PhoneSettings prefs=new PhoneSettings(service);prefs.p.edit().clear().putBoolean("evaluation_enabled",false).apply();
    Bitmap frame;try(InputStream in=getClass().getClassLoader().getResourceAsStream("fixtures/chesscom-starting-board.png")){frame=BitmapFactory.decodeStream(in).copy(Bitmap.Config.ARGB_8888,true);}
    set(service,"settings",prefs);set(service,"overlay",new ArrowOverlay(service));set(service,"reader",new BoardReader(service));set(service,"cachedFrame",frame);set(service,"lastScan",-1000L);
    ScreenService.running=true;ScreenService.phoneVisible=false;ScreenService.fen="";long reads=ScreenService.reads;
    try{
      tick(service);assertEquals(reads+1,ScreenService.reads);
      Canvas canvas=new Canvas(frame);Paint paint=new Paint();paint.setColor(0xffbaca44);int cell=frame.getWidth()/8;canvas.drawRect(5*cell,4*cell,6*cell,5*cell,paint);
      SystemClock.sleep(32);tick(service);
      assertTrue(ScreenService.status,ScreenService.fen.startsWith(START+" w KQkq"));assertEquals(reads+2,ScreenService.reads);
    }finally{controller.destroy();Shadows.shadowOf(Looper.getMainLooper()).idle();}
  }
  @Test public void semanticConfirmationRejectsMovedPiecesOrientationAndGeometry(){
    BoardReader.Read a=new BoardReader.Read(new Rect(0,100,800,900),START,true,.99f);
    assertTrue(ScreenService.sameRead(a,new BoardReader.Read(new Rect(1,101,801,901),START,true,.99f)));
    assertFalse(ScreenService.sameRead(a,new BoardReader.Read(new Rect(0,100,800,900),START,false,.99f)));
    assertFalse(ScreenService.sameRead(a,new BoardReader.Read(new Rect(0,150,800,950),START,true,.99f)));
    assertFalse(ScreenService.sameRead(a,new BoardReader.Read(new Rect(0,100,800,900),"rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",true,.99f)));
  }
  @Test public void splashThenBoardThenDifferentPageRecoversWithoutRestartOrMove()throws Exception{
    var controller=Robolectric.buildService(ScreenService.class).create();ScreenService service=controller.get();
    PhoneSettings prefs=new PhoneSettings(service);prefs.p.edit().clear().putBoolean("evaluation_enabled",false).apply();
    Bitmap splash=Bitmap.createBitmap(1080,2340,Bitmap.Config.ARGB_8888);splash.eraseColor(0xff262421);
    Bitmap board;try(InputStream in=getClass().getClassLoader().getResourceAsStream("fixtures/chesscom-starting-board.png")){board=BitmapFactory.decodeStream(in);}
    set(service,"settings",prefs);set(service,"overlay",new ArrowOverlay(service));set(service,"reader",new BoardReader(service));set(service,"cachedFrame",splash);set(service,"lastScan",-1000L);
    ScreenService.running=true;ScreenService.phoneVisible=false;ScreenService.fen="";
    try{
      tick(service);assertEquals("No board should be invented on a splash screen","",ScreenService.fen);
      long splashReads=ScreenService.reads;for(int i=0;i<3;i++){SystemClock.sleep(125);tick(service);}assertEquals("An unchanged rejected capture must not repeat neural discovery",splashReads,ScreenService.reads);
      for(int top:new int[]{686,375}){
        Bitmap phone=PhoneBoardLayoutTest.layout(board,1080,2340,0,top,1080);set(service,"cachedFrame",phone);set(service,"needsRead",true);
        for(int i=0;i<5;i++){SystemClock.sleep(125);tick(service);}
        Field field=ScreenService.class.getDeclaredField("target");field.setAccessible(true);Rect target=(Rect)field.get(service);
        assertNotNull("Board should be acquired on page y="+top,target);assertTrue(target.toString(),Math.abs(target.top-top)<5);
        assertTrue(ScreenService.status,ScreenService.fen.startsWith(START+" w KQkq"));
        if(top==686)phone.recycle();
      }
    }finally{controller.destroy();Shadows.shadowOf(Looper.getMainLooper()).idle();splash.recycle();board.recycle();}
  }
  @Test public void blackCaptureSkipsNeuralSearchAndAutomaticallyRecovers()throws Exception{
    var controller=Robolectric.buildService(ScreenService.class).create();ScreenService service=controller.get();
    PhoneSettings prefs=new PhoneSettings(service);prefs.p.edit().clear().putBoolean("evaluation_enabled",false).apply();Bitmap black=Bitmap.createBitmap(1080,2340,Bitmap.Config.ARGB_8888);black.eraseColor(Color.BLACK);
    set(service,"settings",prefs);set(service,"overlay",new ArrowOverlay(service));set(service,"reader",new BoardReader(service));set(service,"cachedFrame",black);set(service,"lastScan",-1000L);ScreenService.running=true;ScreenService.phoneVisible=false;long reads=ScreenService.reads;
    try{
      tick(service);SystemClock.sleep(450);tick(service);assertEquals(reads,ScreenService.reads);assertTrue(ScreenService.status,ScreenService.status.contains("capture is blocked"));
      Bitmap board;try(InputStream in=getClass().getClassLoader().getResourceAsStream("fixtures/chesscom-starting-board.png")){board=BitmapFactory.decodeStream(in);}
      Bitmap phone=PhoneBoardLayoutTest.layout(board,1080,2340,0,686,1080);board.recycle();set(service,"cachedFrame",phone);set(service,"needsRead",true);
      tick(service);SystemClock.sleep(32);tick(service);assertTrue(ScreenService.status,ScreenService.fen.startsWith(START+" w KQkq"));assertEquals(reads+1,ScreenService.reads);
    }finally{controller.destroy();Shadows.shadowOf(Looper.getMainLooper()).idle();black.recycle();}
  }
}
