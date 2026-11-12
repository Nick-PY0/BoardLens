package app.boardlens.companion;

/** Exact public Maia 2/3 feature layouts; a1 is square 0, Black mirrors ranks/colors. */
final class MaiaEncoding {
 static int ratingBucket(int elo){return elo<1100?0:elo>=2000?10:1+(elo-1100)/100;}
 static String canonicalMove(String move,boolean white){
  if(white)return move;
  return ""+move.charAt(0)+(char)('9'-move.charAt(1)+'0')+move.charAt(2)+(char)('9'-move.charAt(3)+'0')+move.substring(4);
 }
 static float[] board(ChessPosition p,boolean maia2){
  int channels=maia2?18:97;float[] out=new float[maia2?18*64:64*97];
  for(int original=0;original<64;original++){
   char piece=p.b[original];if(piece=='.')continue;
   int sq=p.white?original:original^56;boolean ours=ChessPosition.color(piece)==p.white;
   int type="pnbrqk".indexOf(Character.toLowerCase(piece))+(ours?0:6);
   if(maia2)out[type*64+sq]=1;
   else for(int history=0;history<8;history++)out[sq*97+history*12+type]=1;
  }
  if(maia2){
   java.util.Arrays.fill(out,12*64,13*64,1);
   String rights=p.white?"KQkq":"kqKQ";
   for(int i=0;i<4;i++)if(p.castle.indexOf(rights.charAt(i))>=0)java.util.Arrays.fill(out,(13+i)*64,(14+i)*64,1);
   if(p.ep>=0)out[17*64+(p.white?p.ep:p.ep^56)]=1;
  }
  return out;
 }
}
