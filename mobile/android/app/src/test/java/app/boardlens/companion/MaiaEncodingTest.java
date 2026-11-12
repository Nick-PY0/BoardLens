package app.boardlens.companion;
import org.junit.Test;import java.io.*;import static org.junit.Assert.*;
public class MaiaEncodingTest {
 @Test public void featuresMatchOfficialPythonIncludingBlackCastlingAndEnPassant()throws Exception{
  for(String name:new String[]{"maia2","maia3-5m"})try(DataInputStream in=new DataInputStream(getClass().getResourceAsStream("/maia/"+name+".bin"))){int count=in.readInt();assertTrue(count>=10);for(int n=0;n<count;n++){String fen=in.readUTF();int rating=in.readInt(),bucket=in.readInt(),dims=in.readInt();for(int i=0;i<dims;i++)in.readInt();float[] expected=new float[in.readInt()];for(int i=0;i<expected.length;i++)expected[i]=in.readFloat();assertArrayEquals(fen,expected,MaiaEncoding.board(new ChessPosition(fen),name.equals("maia2")),0f);assertEquals(bucket,name.equals("maia2")?MaiaEncoding.ratingBucket(rating):rating);}}
 }
 @Test public void blackMoveMirroringPreservesPromotions(){assertEquals("h2h1n",MaiaEncoding.canonicalMove("h7h8n",false));assertEquals("e8g8",MaiaEncoding.canonicalMove("e1g1",false));assertEquals("e2e4",MaiaEncoding.canonicalMove("e2e4",true));}
}
