package app.boardlens.companion;
import android.graphics.Bitmap;
import java.nio.ByteBuffer;

/** Copy actual RGBA pixels only; row padding (including the last row) is optional. */
final class FramePixels {
 private ByteBuffer packed;
 Bitmap bitmap(ByteBuffer source,int width,int height,int rowStride,int pixelStride){
  if(width<1||height<1||pixelStride<4||rowStride<(long)(width-1)*pixelStride+4)return null;
  int base=source.position();long end=base+(long)(height-1)*rowStride+(long)(width-1)*pixelStride+4;
  if(end>source.limit()||(long)width*height>Integer.MAX_VALUE/4)return null;
  ByteBuffer rgba;
  if(pixelStride==4&&rowStride==width*4){rgba=source.duplicate();rgba.limit(base+width*height*4);}
  else{
   int size=width*height*4;
   if(packed==null||packed.capacity()<size)packed=ByteBuffer.allocateDirect(size);
   rgba=packed;rgba.clear();rgba.limit(size);ByteBuffer row=source.duplicate();
   for(int y=0;y<height;y++){
    int start=base+y*rowStride;
    if(pixelStride==4){row.limit(source.limit());row.position(start);row.limit(start+width*4);rgba.put(row);}
    else for(int x=0;x<width;x++)for(int c=0;c<4;c++)rgba.put(source.get(start+x*pixelStride+c));
   }
   rgba.flip();
  }
  Bitmap result=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888);result.copyPixelsFromBuffer(rgba);return result;
 }
}
