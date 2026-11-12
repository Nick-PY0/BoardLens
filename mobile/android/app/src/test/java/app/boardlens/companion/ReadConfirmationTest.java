package app.boardlens.companion;
import org.junit.Test;import static org.junit.Assert.*;import java.util.Arrays;
public class ReadConfirmationTest {
 private int[] pixels(){int[] p=new int[9216];Arrays.fill(p,0xffabcdef);return p;}
 @Test public void oneRecognitionConfirmsAStillFrameWithoutAnotherInference(){ReadConfirmation<String> c=new ReadConfirmation<>();int[] p=pixels();c.set("recognized FEN",p,100);assertNull(c.poll(p,115));assertEquals("recognized FEN",c.poll(p,132));c.clear();assertNull(c.poll(p,200));}
 @Test public void animationInvalidatesTheCandidate(){ReadConfirmation<String> c=new ReadConfirmation<>();int[] p=pixels();c.set("mid-animation",p,0);for(int i=100;i<150;i++)p[i]=0xff111111;assertNull(c.poll(p,40));assertNull(c.poll(pixels(),80));}
 @Test public void coveredOverlayPixelsDoNotPretendTheBoardMoved(){ReadConfirmation<String> c=new ReadConfirmation<>();int[] p=pixels(),changed=pixels();for(int i=0;i<300;i++)p[i]=0;c.set("position",p,0);for(int i=0;i<300;i++)changed[i]=0xff111111;assertEquals("position",c.poll(changed,32));}
}
