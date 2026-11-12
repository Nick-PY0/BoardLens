package app.boardlens.companion;
import java.nio.ByteBuffer;import org.junit.Test;import static org.junit.Assert.*;
public class FrameFingerprintTest {
 @Test public void rgbaPaddingOffsetAndOverlayMasksMatchBoardSamples(){ByteBuffer b=ByteBuffer.allocate(4+24*2);b.position(4);for(int y=0;y<2;y++)for(int x=0;x<4;x++){int p=4+y*24+x*4;b.put(p,(byte)(10+x));b.put(p+1,(byte)(20+y));b.put(p+2,(byte)30);b.put(p+3,(byte)255);}int[] f=FrameFingerprint.read(b,4,2,24,4,1,0,4,2,(x,y)->x==2);assertEquals(0xff0b141e,f[0]);assertEquals(0,f[48]);assertEquals(0xff0d151e,f[f.length-1]);assertEquals(4,b.position());}
 @Test public void invalidOrTruncatedCaptureFallsBackToNormalRead(){assertNull(FrameFingerprint.read(ByteBuffer.allocate(8),4,2,16,4,0,0,4,2,(x,y)->false));assertNull(FrameFingerprint.read(ByteBuffer.allocate(32),4,2,16,4,-1,0,4,2,(x,y)->false));}
}
