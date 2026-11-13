package app.boardlens.companion;
import android.graphics.Bitmap;

/** A blank capture is not evidence of a board. Do not infer or bypass protection. */
final class CaptureVisibility {
 static boolean blank(Bitmap frame,FrameFingerprint.Mask mask){
  int bright=0,total=0;
  for(int y=0;y<48;y++)for(int x=0;x<32;x++){
   int xx=(int)((.02+(x+.5)*.96/32)*frame.getWidth()),yy=(int)((.12+(y+.5)*.76/48)*frame.getHeight());
   if(mask.covers(xx,yy))continue;
   int p=frame.getPixel(xx,yy);total++;
   if((p>>16&255)+(p>>8&255)+(p&255)>24&&++bright>16)return false;
  }
  return total>=1000&&bright<=total*.01;
 }
}
