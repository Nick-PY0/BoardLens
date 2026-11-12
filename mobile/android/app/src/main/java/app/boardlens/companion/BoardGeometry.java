package app.boardlens.companion;

/** Immutable unit-square to screen homography; no Android dependency. */
final class BoardGeometry {
  private final double[] h;
  final double[] corners;
  BoardGeometry(double... points){
    if(points.length!=8)throw new IllegalArgumentException("Four board corners required");
    corners=points.clone();for(double p:points)if(!Double.isFinite(p))throw new IllegalArgumentException("Invalid board corner");
    double area=0;for(int i=0;i<4;i++){int j=(i+1)%4;area+=points[2*i]*points[2*j+1]-points[2*i+1]*points[2*j];}
    if(area<128)throw new IllegalArgumentException("Board must be clockwise and nondegenerate");
    for(int i=0;i<4;i++){int j=(i+1)%4,k=(i+2)%4;double cross=(points[2*j]-points[2*i])*(points[2*k+1]-points[2*j+1])-(points[2*j+1]-points[2*i+1])*(points[2*k]-points[2*j]);if(cross<=0)throw new IllegalArgumentException("Board must be convex");}
    double[][] a=new double[8][9];double[] uv={0,0,1,0,1,1,0,1};
    for(int i=0;i<4;i++){double u=uv[2*i],v=uv[2*i+1],x=points[2*i],y=points[2*i+1];a[2*i]=new double[]{u,v,1,0,0,0,-u*x,-v*x,x};a[2*i+1]=new double[]{0,0,0,u,v,1,-u*y,-v*y,y};}
    for(int col=0;col<8;col++){int pivot=col;for(int row=col+1;row<8;row++)if(Math.abs(a[row][col])>Math.abs(a[pivot][col]))pivot=row;if(Math.abs(a[pivot][col])<1e-10)throw new IllegalArgumentException("Degenerate projection");double[] tmp=a[col];a[col]=a[pivot];a[pivot]=tmp;double d=a[col][col];for(int j=col;j<9;j++)a[col][j]/=d;for(int row=0;row<8;row++)if(row!=col){double f=a[row][col];for(int j=col;j<9;j++)a[row][j]-=f*a[col][j];}}
    h=new double[9];for(int i=0;i<8;i++)h[i]=a[i][8];h[8]=1;
  }
  static BoardGeometry rectangle(double left,double top,double right,double bottom){return new BoardGeometry(left,top,right,top,right,bottom,left,bottom);}
  double[] map(double u,double v){double d=h[6]*u+h[7]*v+1;return new double[]{(h[0]*u+h[1]*v+h[2])/d,(h[3]*u+h[4]*v+h[5])/d};}
  double[] unmap(double x,double y){double a=h[0]-x*h[6],b=h[1]-x*h[7],c=x-h[2],d=h[3]-y*h[6],e=h[4]-y*h[7],f=y-h[5],det=a*e-b*d;if(Math.abs(det)<1e-10)throw new IllegalArgumentException("Invalid inverse");return new double[]{(c*e-b*f)/det,(a*f-c*d)/det};}
  double[] square(String algebraic,boolean whiteBottom){if(algebraic.length()!=2||algebraic.charAt(0)<'a'||algebraic.charAt(0)>'h'||algebraic.charAt(1)<'1'||algebraic.charAt(1)>'8')throw new IllegalArgumentException("Invalid square");int file=algebraic.charAt(0)-'a',rank=algebraic.charAt(1)-'1';return map(((whiteBottom?file:7-file)+.5)/8,((whiteBottom?7-rank:rank)+.5)/8);}
  double cellWidth(int row,int col){double[] a=map(col/8.,(row+.5)/8.),b=map((col+1)/8.,(row+.5)/8.);return Math.hypot(b[0]-a[0],b[1]-a[1]);}
  BoardGeometry inset(double amount){double[] a=map(amount,amount),b=map(1-amount,amount),c=map(1-amount,1-amount),d=map(amount,1-amount);return new BoardGeometry(a[0],a[1],b[0],b[1],c[0],c[1],d[0],d[1]);}
  double[] bounds(){double l=Double.MAX_VALUE,t=l,r=-l,b=-l;for(int i=0;i<4;i++){l=Math.min(l,corners[2*i]);r=Math.max(r,corners[2*i]);t=Math.min(t,corners[2*i+1]);b=Math.max(b,corners[2*i+1]);}return new double[]{l,t,r,b};}
}
