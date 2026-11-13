package app.boardlens.companion;
import android.app.Application;import android.graphics.*;import org.junit.*;import org.junit.runner.RunWith;import org.robolectric.annotation.*;import static org.junit.Assert.*;
@RunWith(org.robolectric.RobolectricTestRunner.class) @Config(sdk=35,application=Application.class) @GraphicsMode(GraphicsMode.Mode.NATIVE)
public class CaptureVisibilityTest {
 @Test public void blackProtectedContentWithSystemBarsDoesNotPretendToBeAChessboard(){
  Bitmap b=Bitmap.createBitmap(1080,2340,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(b);c.drawColor(Color.BLACK);Paint p=new Paint();p.setColor(Color.WHITE);c.drawRect(0,0,1080,90,p);c.drawRect(0,2250,1080,2340,p);
  assertTrue(CaptureVisibility.blank(b,(x,y)->false));p.setColor(Color.CYAN);c.drawRect(500,1000,520,1500,p);assertTrue(CaptureVisibility.blank(b,(x,y)->x>=500&&x<=520&&y>=1000&&y<=1500));b.recycle();
 }
 @Test public void evenASmallBoardOrDarkVisibleAppIsNotClassedAsBlackCapture(){
  Bitmap b=Bitmap.createBitmap(1080,2340,Bitmap.Config.ARGB_8888);b.eraseColor(0xff242424);assertFalse(CaptureVisibility.blank(b,(x,y)->false));
  b.eraseColor(Color.BLACK);Canvas c=new Canvas(b);Paint p=new Paint();p.setColor(0xffeeeed2);c.drawRect(400,600,600,800,p);assertFalse(CaptureVisibility.blank(b,(x,y)->false));b.recycle();
 }
}
