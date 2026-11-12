package app.boardlens.companion;

import android.graphics.Bitmap;
import android.graphics.Color;
import java.util.*;
import org.opencv.android.OpenCVLoader;
import org.opencv.android.Utils;
import org.opencv.core.*;
import org.opencv.imgproc.Imgproc;

/** Perspective candidates are verified by alternating square colors, never by a frame alone. */
final class ProjectedBoards {
  private static boolean loaded;
  static synchronized boolean ready(){if(!loaded){loaded=OpenCVLoader.initLocal();if(loaded)Core.setNumThreads(1);}return loaded;}
  static List<BoardGeometry> detect(Bitmap image){
    List<BoardGeometry> found=new ArrayList<>();if(!ready())return found;
    double scale=Math.min(1,960./Math.max(image.getWidth(),image.getHeight()));Bitmap small=Bitmap.createScaledBitmap(image,(int)Math.round(image.getWidth()*scale),(int)Math.round(image.getHeight()*scale),true);
    Mat rgba=new Mat(),gray=new Mat(),edge=new Mat(),hierarchy=new Mat();List<MatOfPoint> contours=new ArrayList<>();
    try{Utils.bitmapToMat(small,rgba);Imgproc.cvtColor(rgba,gray,Imgproc.COLOR_RGBA2GRAY);Imgproc.GaussianBlur(gray,gray,new Size(3,3),0);Imgproc.Canny(gray,edge,35,100);Imgproc.findContours(edge,contours,hierarchy,Imgproc.RETR_LIST,Imgproc.CHAIN_APPROX_SIMPLE);
      contours.sort((a,b)->Double.compare(Math.abs(Imgproc.contourArea(b)),Math.abs(Imgproc.contourArea(a))));
      int checked=0;
      for(MatOfPoint contour:contours){double area=Math.abs(Imgproc.contourArea(contour));if(area<180*180*scale*scale)break;if(checked++>100)break;
        MatOfPoint2f curve=new MatOfPoint2f(contour.toArray()),approx=new MatOfPoint2f();try{
          Imgproc.approxPolyDP(curve,approx,.018*Imgproc.arcLength(curve,true),true);Point[] p=approx.toArray();if(p.length!=4)continue;
          Arrays.sort(p,Comparator.comparingDouble(v->v.y));Point tl=p[0].x<p[1].x?p[0]:p[1],tr=p[0].x<p[1].x?p[1]:p[0],bl=p[2].x<p[3].x?p[2]:p[3],br=p[2].x<p[3].x?p[3]:p[2];
          BoardGeometry outer;try{outer=new BoardGeometry(tl.x/scale,tl.y/scale,tr.x/scale,tr.y/scale,br.x/scale,br.y/scale,bl.x/scale,bl.y/scale);}catch(IllegalArgumentException e){continue;}
          BoardGeometry best=null;double score=.82;
          for(double inset:new double[]{0,.0125,.025,.0375,.05,.0625,.075}){BoardGeometry g=outer.inset(inset);double s=checker(image,g);if(s>score){score=s;best=g;}}
          if(best==null)continue;double[] bounds=best.bounds();boolean duplicate=false;for(BoardGeometry prior:found){double[] b=prior.bounds();if(Math.abs(b[0]-bounds[0])+Math.abs(b[1]-bounds[1])<30&&Math.abs((b[2]-b[0])-(bounds[2]-bounds[0]))<30)duplicate=true;}if(!duplicate)found.add(best);if(found.size()>=6)break;
        }finally{curve.release();approx.release();}
      }
      // A 3D piece can hide the outside border. Empty square quads still
      // define the board plane; extrapolate their grid and verify all squares.
      int tiles=0;
      for(MatOfPoint contour:contours){
        double area=Math.abs(Imgproc.contourArea(contour));if(area>gray.cols()*gray.rows()/25.)continue;if(area<200)break;if(tiles++>32||found.size()>=6)break;
        MatOfPoint2f curve=new MatOfPoint2f(contour.toArray()),approx=new MatOfPoint2f();
        try{Imgproc.approxPolyDP(curve,approx,.025*Imgproc.arcLength(curve,true),true);Point[] p=approx.toArray();if(p.length!=4)continue;Arrays.sort(p,Comparator.comparingDouble(v->v.y));Point tl=p[0].x<p[1].x?p[0]:p[1],tr=p[0].x<p[1].x?p[1]:p[0],bl=p[2].x<p[3].x?p[2]:p[3],br=p[2].x<p[3].x?p[3]:p[2];BoardGeometry tile;
          try{tile=new BoardGeometry(tl.x/scale,tl.y/scale,tr.x/scale,tr.y/scale,br.x/scale,br.y/scale,bl.x/scale,bl.y/scale);}catch(IllegalArgumentException e){continue;}
          double tw=Math.hypot(tr.x-tl.x,tr.y-tl.y),th=Math.hypot(bl.x-tl.x,bl.y-tl.y);if(tw/th<.6||tw/th>2.2)continue;
          for(int row=0;row<8;row++)for(int col=0;col<8;col++){
            double[] a=tile.map(-col,-row),b=tile.map(8-col,-row),c=tile.map(8-col,8-row),d=tile.map(-col,8-row);BoardGeometry board;
            try{board=new BoardGeometry(a[0],a[1],b[0],b[1],c[0],c[1],d[0],d[1]);}catch(IllegalArgumentException e){continue;}
            double[] bb=board.bounds();if(bb[0]<0||bb[1]<0||bb[2]>image.getWidth()||bb[3]>image.getHeight()||bb[2]-bb[0]<180||bb[3]-bb[1]<120)continue;
            if(checker(image,board)<.86)continue;boolean duplicate=false;for(BoardGeometry prior:found){double[] pb=prior.bounds();if(Math.abs(pb[0]-bb[0])+Math.abs(pb[1]-bb[1])+Math.abs(pb[2]-bb[2])+Math.abs(pb[3]-bb[3])<40)duplicate=true;}if(!duplicate)found.add(board);
          }
        }finally{curve.release();approx.release();}
      }
    }finally{for(MatOfPoint c:contours)c.release();rgba.release();gray.release();edge.release();hierarchy.release();if(small!=image)small.recycle();}
    return found;
  }
  static double checker(Bitmap image,BoardGeometry geometry){
    int[][] samples=new int[2][32];int[] n={0,0};int[] colors=new int[64];
    for(int row=0;row<8;row++)for(int col=0;col<8;col++){
      int[][] rgb=new int[3][4];int at=0;
      for(double yy:new double[]{.12,.88})for(double xx:new double[]{.12,.88}){double[] p=geometry.map((col+xx)/8,(row+yy)/8);int x=(int)Math.round(p[0]),y=(int)Math.round(p[1]);if(x<0||y<0||x>=image.getWidth()||y>=image.getHeight())return 0;int pixel=image.getPixel(x,y);rgb[0][at]=Color.red(pixel);rgb[1][at]=Color.green(pixel);rgb[2][at++]=Color.blue(pixel);}
      int[] m=new int[3];for(int c=0;c<3;c++){Arrays.sort(rgb[c]);m[c]=(rgb[c][1]+rgb[c][2])/2;}int pixel=Color.rgb(m[0],m[1],m[2]);colors[row*8+col]=pixel;samples[(row+col)%2][n[(row+col)%2]++]=pixel;
    }
    int[] center=new int[2];for(int parity=0;parity<2;parity++){int[][] rgb=new int[3][32];for(int i=0;i<32;i++){rgb[0][i]=Color.red(samples[parity][i]);rgb[1][i]=Color.green(samples[parity][i]);rgb[2][i]=Color.blue(samples[parity][i]);}for(int[] a:rgb)Arrays.sort(a);center[parity]=Color.rgb(rgb[0][16],rgb[1][16],rgb[2][16]);}
    double contrast=distance(center[0],center[1]);if(contrast<600)return 0;int good=0;for(int r=0;r<8;r++)for(int c=0;c<8;c++)if(distance(colors[r*8+c],center[(r+c)%2])<Math.max(700,contrast*.18))good++;return good/64.;
  }
  private static double distance(int a,int b){double r=Color.red(a)-Color.red(b),g=Color.green(a)-Color.green(b),bl=Color.blue(a)-Color.blue(b);return r*r+g*g+bl*bl;}
}
