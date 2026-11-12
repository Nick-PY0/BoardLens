package app.boardlens.companion;
import org.junit.Test;
import static org.junit.Assert.*;
public class RecognizedPositionTest {
 @Test public void rejectsWrongPawnColorInAnOtherwiseCompleteStartingRead(){
  char[] position="rnbqkbnrpppppppp................................PPPPPPPPRNBQKBNR".toCharArray();
  assertTrue(BoardReader.plausible(position));position[52]='p';assertFalse(BoardReader.plausible(position));
 }
 @Test public void promotionsRemainPossibleButAdjacentKingsDoNot(){
  char[] position=".......k............................................Q..QK.......".toCharArray();
  assertEquals(64,position.length);assertTrue(BoardReader.plausible(position));position[7]='.';position[57]='k';assertFalse(BoardReader.plausible(position));
 }
}
