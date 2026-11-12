package app.boardlens.companion;

/** Position the passive evaluation outside the board whenever space allows. */
final class OverlayLayout {
 record Box(int left,int top,int right,int bottom,boolean vertical){}
 static Box place(double[] board,int width,int height,float density,int topInset,int bottomInset,String mode){
  int gap=Math.max(4,Math.round(8*density)),cw=Math.min(width-2*gap,Math.round(168*density)),ch=Math.round(44*density),vw=Math.round(40*density),vh=Math.min(Math.round(176*density),height-topInset-bottomInset-2*gap);
  int safeTop=topInset+gap,safeBottom=height-bottomInset-gap,x=(width-cw)/2,y=safeTop;boolean vertical=false;
  if(mode.equals("Auto")){
   if(board[1]-gap-ch>=safeTop)y=(int)board[1]-gap-ch;
   else if(board[3]+gap+ch<=safeBottom)y=(int)board[3]+gap;
   else if(board[0]-gap-vw>=gap){x=(int)board[0]-gap-vw;vertical=true;}
   else if(board[2]+gap+vw<=width-gap){x=(int)board[2]+gap;vertical=true;}
  }else if(mode.equals("Bottom"))y=safeBottom-ch;
  else if(mode.equals("Left")||mode.equals("Right")){vertical=true;x=mode.equals("Left")?gap:width-gap-vw;}
  if(vertical){cw=vw;ch=vh;y=Math.max(safeTop,Math.min(safeBottom-ch,(int)((board[1]+board[3]-ch)/2)));}
  else x=Math.max(gap,Math.min(width-gap-cw,(int)((board[0]+board[2]-cw)/2)));
  return new Box(x,y,x+cw,y+ch,vertical);
 }
}
