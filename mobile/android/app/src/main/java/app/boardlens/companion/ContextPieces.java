package app.boardlens.companion;

import ai.onnxruntime.*;
import android.content.Context;
import android.graphics.*;
import java.nio.FloatBuffer;
import java.util.*;

/** Screen-space contexts retain 3D crowns above their board squares. */
final class ContextPieces implements AutoCloseable {
 private final OrtEnvironment env=OrtEnvironment.getEnvironment();private final OrtSession session;
 boolean projectedArtwork;
 ContextPieces(Context c)throws Exception{
  OrtSession loaded=null;
  try(var in=c.getAssets().open("models/chess-context-v3.onnx");var options=new OrtSession.SessionOptions()){
   options.setIntraOpNumThreads(1);loaded=env.createSession(Streams.read(in,8000000),options);
  }catch(java.io.FileNotFoundException unavailable){/* Development builds without new weights retain 2D recognition. */}
  session=loaded;
 }
 boolean verifyFlat(Bitmap image,BoardGeometry geometry,BoardReader.Read flat)throws Exception{
  if(session==null)return true;
  StringBuilder expanded=new StringBuilder();for(char ch:flat.placement().toCharArray()){if(ch=='/')continue;if(ch>='1'&&ch<='8')for(int i=0;i<ch-'0';i++)expanded.append('.');else expanded.append(ch);}
  String canonical=expanded.toString();if(canonical.length()!=64)return false;String shown=flat.whiteBottom()?canonical:expanded.reverse().toString();List<Integer> occupied=new ArrayList<>();for(int i=0;i<64;i++)if(shown.charAt(i)!='.')occupied.add(i);if(occupied.isEmpty())return false;
  int count=Math.min(4,occupied.size());int[] pixels=new int[image.getWidth()*image.getHeight()];image.getPixels(pixels,0,image.getWidth(),0,0,image.getWidth(),image.getHeight());float[] input=new float[count*6144];int[] chosen=new int[count];
  for(int i=0;i<count;i++){int square=occupied.get(i*(occupied.size()-1)/Math.max(1,count-1));chosen[i]=square;int row=square/8,col=square%8;double[] center=geometry.map((col+.5)/8,(row+.5)/8);double cell=geometry.cellWidth(row,col);
   for(int y=0;y<96;y++)for(int x=0;x<64;x++){int pixel=bilinear(pixels,image.getWidth(),image.getHeight(),center[0]+(-.75+(x+.5)*1.5/64)*cell-.5,center[1]+(-1.5+(y+.5)*2.15/96)*cell-.5);input[i*6144+y*64+x]=(Color.red(pixel)*.299f+Color.green(pixel)*.587f+Color.blue(pixel)*.114f)/255f;}
  }
  try(OnnxTensor tensor=OnnxTensor.createTensor(env,FloatBuffer.wrap(input),new long[]{count,6144});OrtSession.Result out=session.run(Collections.singletonMap("patches",tensor))){float[][] p=(float[][])out.get(0).getValue(),z=(float[][])out.get(1).getValue();String labels=".KQRBNPkqrbnp";for(int i=0;i<count;i++){int best=0;for(int j=1;j<13;j++)if(p[i][j]>p[i][best])best=j;if(z[i][0]>.1||p[i][0]>.2)return false;}}return true;
 }
 BoardReader.Read classify(Bitmap image,BoardGeometry geometry,String orientation)throws Exception{
  projectedArtwork=false;if(session==null)return null;
  double[] bounds=geometry.bounds();if(bounds[0]<0||bounds[1]<0||bounds[2]>image.getWidth()||bounds[3]>image.getHeight()||bounds[2]-bounds[0]<160||bounds[3]-bounds[1]<120)return null;
  if(ProjectedBoards.checker(image,geometry)<.82)return null;
  int[] pixels=new int[image.getWidth()*image.getHeight()];image.getPixels(pixels,0,image.getWidth(),0,0,image.getWidth(),image.getHeight());
  float[] input=new float[64*6144];
  for(int row=0;row<8;row++)for(int col=0;col<8;col++){
   double[] center=geometry.map((col+.5)/8,(row+.5)/8);double cell=geometry.cellWidth(row,col);
   for(int y=0;y<96;y++)for(int x=0;x<64;x++){
    double px=center[0]+(-.75+(x+.5)*1.5/64)*cell,py=center[1]+(-1.5+(y+.5)*2.15/96)*cell;
    int pixel=bilinear(pixels,image.getWidth(),image.getHeight(),px-.5,py-.5);input[(row*8+col)*6144+y*64+x]=(Color.red(pixel)*.299f+Color.green(pixel)*.587f+Color.blue(pixel)*.114f)/255f;
   }
  }
  char[] shown=new char[64];float sum=0,min=1,three=0;int occupied=0;String labels=".KQRBNPkqrbnp";
  try(OnnxTensor tensor=OnnxTensor.createTensor(env,FloatBuffer.wrap(input),new long[]{64,6144});OrtSession.Result out=session.run(Collections.singletonMap("patches",tensor))){
   float[][] probs=(float[][])out.get(0).getValue(),projection=(float[][])out.get(1).getValue();
   for(int i=0;i<64;i++){int best=0;for(int j=1;j<13;j++)if(probs[i][j]>probs[i][best])best=j;shown[i]=labels.charAt(best);sum+=probs[i][best];min=Math.min(min,probs[i][best]);if(best>0){three+=projection[i][0];occupied++;}}
  }
  projectedArtwork=occupied>0&&three/occupied>.65;
  if(min<.97||sum/64<.99)return null;
  int wk=0,bk=0,wp=0,bp=0;double wy=0,by=0;int whiteKing=0,blackKing=0;
  for(int i=0;i<64;i++){char ch=shown[i];if(ch=='K'){wk++;whiteKing=i/8;}if(ch=='k'){bk++;blackKing=i/8;}if(ch=='P'){wp++;wy+=i/8;}if(ch=='p'){bp++;by+=i/8;}}
  if(wk!=1||bk!=1)return null;
  boolean bottom=orientation.equals("White at bottom")||!orientation.equals("Black at bottom")&&(wp>0&&bp>0?wy/wp>by/bp:whiteKing>blackKing);
  StringBuilder placement=new StringBuilder();for(int row=0;row<8;row++){int empty=0;for(int col=0;col<8;col++){char ch=shown[bottom?row*8+col:63-row*8-col];if(ch=='.')empty++;else{if(empty>0){placement.append(empty);empty=0;}placement.append(ch);}}if(empty>0)placement.append(empty);if(row<7)placement.append('/');}
  return new BoardReader.Read(new Rect((int)Math.floor(bounds[0]),(int)Math.floor(bounds[1]),(int)Math.ceil(bounds[2]),(int)Math.ceil(bounds[3])),placement.toString(),bottom,sum/64,geometry);
 }
 private static int bilinear(int[] pixels,int width,int height,double x,double y){
  if(x<0||y<0||x>=width-1||y>=height-1)return Color.rgb(36,39,43);
  int xx=(int)x,yy=(int)y;double fx=x-xx,fy=y-yy;int a=pixels[yy*width+xx],b=pixels[yy*width+xx+1],c=pixels[(yy+1)*width+xx],d=pixels[(yy+1)*width+xx+1];
  return Color.rgb(mix(Color.red(a),Color.red(b),Color.red(c),Color.red(d),fx,fy),mix(Color.green(a),Color.green(b),Color.green(c),Color.green(d),fx,fy),mix(Color.blue(a),Color.blue(b),Color.blue(c),Color.blue(d),fx,fy));
 }
 private static int mix(int a,int b,int c,int d,double x,double y){return (int)Math.round((a*(1-x)+b*x)*(1-y)+(c*(1-x)+d*x)*y);}
 public void close()throws OrtException{if(session!=null)session.close();}
}
