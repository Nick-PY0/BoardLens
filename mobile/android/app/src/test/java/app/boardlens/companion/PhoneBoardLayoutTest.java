package app.boardlens.companion;
import android.app.Application;
import android.graphics.*;
import java.io.*;
import java.util.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class PhoneBoardLayoutTest {
 static final String START="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR";
 static Bitmap layout(Bitmap board,int width,int height,int left,int top,int side){
  Bitmap image=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(image);c.drawColor(0xff262421);
  Paint paint=new Paint(Paint.FILTER_BITMAP_FLAG);c.drawBitmap(board,null,new Rect(left,top,left+side,top+side),paint);return image;
 }
 @Test public void firstScanHandlesFlushEdgesAndDifferentPageHeaders()throws Exception{
  List<String> errors=new ArrayList<>();
  try(InputStream in=getClass().getClassLoader().getResourceAsStream("fixtures/chesscom-starting-board.png")){
   Bitmap board=BitmapFactory.decodeStream(in);
   for(int top:new int[]{259,375,521,686,777}){
    Bitmap image=layout(board,1080,2340,0,top,1080);
    try(BoardReader reader=new BoardReader(RuntimeEnvironment.getApplication())){
     long start=System.nanoTime();BoardReader.Read read=reader.read(image,null,"Auto");
     String result=read==null?"missing "+reader.diagnostic:read.placement()+" "+read.rect();
     System.out.println("Edge board y="+top+" "+((System.nanoTime()-start)/1000000)+"ms "+result);
     if(read==null||!read.placement().equals(START))errors.add("y="+top+" "+result);
    }finally{image.recycle();}
   }
   board.recycle();
  }
  assertTrue(errors.toString(),errors.isEmpty());
 }
 @Test public void onePixelCandidateRoundingDoesNotRejectAVisibleBoard()throws Exception{
  try(InputStream in=getClass().getClassLoader().getResourceAsStream("fixtures/chesscom-starting-board.png");BoardReader reader=new BoardReader(RuntimeEnvironment.getApplication())){
   Bitmap board=BitmapFactory.decodeStream(in),phone=layout(board,1080,2340,0,686,1080);
   for(Rect rect:new Rect[]{new Rect(0,686,1080,1767),new Rect(-1,686,1080,1766),new Rect(0,686,1081,1766)}){
    BoardReader.Read read=reader.classify(phone,rect,"Auto");assertNotNull(rect+" "+reader.diagnostic,read);assertEquals(START,read.placement());
    assertEquals(read.rect().width(),read.rect().height());
   }
   assertNull(reader.classify(phone,new Rect(-40,686,1040,1766),"Auto"));
   assertNull(reader.classify(phone,new Rect(0,686,1080,1650),"Auto"));board.recycle();phone.recycle();
  }
 }
 @Test public void discoveryFindsPiecesDespiteAnotherEmptyCheckerboard()throws Exception{
  try(InputStream in=getClass().getClassLoader().getResourceAsStream("fixtures/chesscom-starting-board.png");BoardReader reader=new BoardReader(RuntimeEnvironment.getApplication())){
   Bitmap board=BitmapFactory.decodeStream(in),phone=layout(board,1080,2340,100,1250,850);Canvas canvas=new Canvas(phone);Paint paint=new Paint();
   for(int row=0;row<8;row++)for(int col=0;col<8;col++){paint.setColor((row+col)%2==0?0xffeeeed2:0xff769656);canvas.drawRect(100+col*106.25f,100+row*106.25f,100+(col+1)*106.25f,100+(row+1)*106.25f,paint);}
   long[] times=new long[5];
   for(int i=0;i<times.length;i++){reader.resetTracking();long start=System.nanoTime();BoardReader.Read read=reader.read(phone,null,"Auto");times[i]=(System.nanoTime()-start)/1000000;assertNotNull(reader.diagnostic,read);assertEquals(START,read.placement());assertTrue(read.rect().toString(),read.rect().top>1200);}
   Arrays.sort(times);System.out.println("Discovery with empty checkerboard median ms: "+times[2]+" runs="+Arrays.toString(times));board.recycle();phone.recycle();
  }
 }
 @Test public void knownFlatBoardRejectsAnEmptyLoadingTransitionAndRecovers()throws Exception{
  try(InputStream in=getClass().getClassLoader().getResourceAsStream("fixtures/chesscom-starting-board.png");BoardReader reader=new BoardReader(RuntimeEnvironment.getApplication())){
   Bitmap board=BitmapFactory.decodeStream(in),phone=layout(board,1080,2340,0,686,1080),empty=Bitmap.createBitmap(1080,2340,Bitmap.Config.ARGB_8888);empty.eraseColor(0xff262421);Canvas canvas=new Canvas(empty);Paint p=new Paint();
   for(int row=0;row<8;row++)for(int col=0;col<8;col++){p.setColor((row+col)%2==0?0xffeeeed2:0xff769656);canvas.drawRect(col*135,686+row*135,(col+1)*135,686+(row+1)*135,p);}
   BoardReader.Read initial=reader.read(phone,null,"Auto");assertNotNull(initial);long[] times=new long[5];
   for(int i=0;i<times.length;i++){long at=System.nanoTime();assertNull("Missing pieces must not become a guessed position",reader.track(empty,initial.rect(),"Auto"));times[i]=(System.nanoTime()-at)/1000000;}
   Arrays.sort(times);System.out.println("Empty loading transition median ms: "+times[2]+" runs="+Arrays.toString(times));assertEquals(START,reader.read(phone,null,"Auto").placement());board.recycle();phone.recycle();empty.recycle();
  }
 }
}
