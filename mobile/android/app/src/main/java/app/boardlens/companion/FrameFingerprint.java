package app.boardlens.companion;
import java.nio.ByteBuffer;

/** Samples RGBA capture pixels directly, avoiding full-screen bitmap copies on idle boards. */
final class FrameFingerprint {
 interface Mask { boolean covers(int x,int y); }
 static int[] read(ByteBuffer pixels,int width,int height,int rowStride,int pixelStride,int left,int top,int right,int bottom,Mask mask){
  if(pixelStride<4||left<0||top<0||right>width||bottom>height||right<=left||bottom<=top)return null;
  int base=pixels.position();long last=base+(long)(bottom-1)*rowStride+(long)(right-1)*pixelStride+4;if(last>pixels.limit())return null;
  int[] result=new int[96*96];
  for(int y=0;y<96;y++)for(int x=0;x<96;x++){
   int xx=left+(int)((x+.5f)*(right-left)/96),yy=top+(int)((y+.5f)*(bottom-top)/96),i=y*96+x;
   if(mask.covers(xx,yy)){result[i]=0;continue;}int at=base+yy*rowStride+xx*pixelStride;
   result[i]=((pixels.get(at+3)&255)<<24)|((pixels.get(at)&255)<<16)|((pixels.get(at+1)&255)<<8)|(pixels.get(at+2)&255);
  }return result;
 }
}
