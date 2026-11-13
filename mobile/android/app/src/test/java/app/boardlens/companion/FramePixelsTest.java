package app.boardlens.companion;
import android.app.Application;
import android.graphics.*;
import java.nio.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.annotation.*;
import static org.junit.Assert.*;
@RunWith(org.robolectric.RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class FramePixelsTest {
 private final FramePixels copier=new FramePixels();
 // Host Skia and Android use different native channel ordering. Check the raw
 // bytes that Bitmap receives, rather than asserting host-specific getPixel colors.
 private void assertRgba(Bitmap image,int x,int y,int r,int g,int b){
  ByteBuffer out=ByteBuffer.allocate(image.getByteCount());image.copyPixelsToBuffer(out);
  int at=y*image.getRowBytes()+x*4;
  assertEquals(r,out.get(at)&255);assertEquals(g,out.get(at+1)&255);assertEquals(b,out.get(at+2)&255);assertEquals(255,out.get(at+3)&255);
 }
 private ByteBuffer pixels(int width,int height,int rowStride,int pixelStride,int base){
  ByteBuffer b=ByteBuffer.allocateDirect(base+(height-1)*rowStride+(width-1)*pixelStride+4);b.position(base);
  for(int y=0;y<height;y++)for(int x=0;x<width;x++){
   int at=base+y*rowStride+x*pixelStride;b.put(at,(byte)(10+x));b.put(at+1,(byte)(20+y));b.put(at+2,(byte)30);b.put(at+3,(byte)255);
  }return b;
 }
 @Test public void captureWithNoLastRowPaddingDecodesAllActualPixels(){
  ByteBuffer b=pixels(4,3,24,4,8);Bitmap image=copier.bitmap(b,4,3,24,4);
  assertNotNull(image);assertEquals(4,image.getWidth());assertEquals(3,image.getHeight());
  assertRgba(image,0,0,10,20,30);assertRgba(image,3,2,13,22,30);assertEquals(8,b.position());image.recycle();
 }
 @Test public void contiguousAndPixelPaddedPlanesDecodeWithoutMovingInput(){
  for(int stride:new int[]{4,8}){ByteBuffer b=pixels(3,2,3*stride,stride,3);Bitmap image=copier.bitmap(b.asReadOnlyBuffer(),3,2,3*stride,stride);
   assertNotNull(image);assertRgba(image,2,1,12,21,30);assertEquals(3,b.position());image.recycle();}
 }
 @Test public void incompleteRowsAreSkippedAndCanRecoverOnNextFrame(){
  ByteBuffer b=pixels(4,3,24,4,0);b.limit(b.limit()-1);assertNull(copier.bitmap(b,4,3,24,4));b.limit(b.capacity());Bitmap image=copier.bitmap(b,4,3,24,4);assertNotNull(image);image.recycle();
  assertNull(copier.bitmap(b,4,3,8,4));assertNull(copier.bitmap(b,4,3,24,2));
 }
 @Test public void repeatedFramesAndResizeReusePackingWithoutKeepingOldPixels(){
  for(int width:new int[]{4,8,3,4}){ByteBuffer b=pixels(width,3,width*4+16,4,0);Bitmap image=copier.bitmap(b,width,3,width*4+16,4);assertRgba(image,width-1,2,9+width,22,30);image.recycle();}
 }
}
