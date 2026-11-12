package app.boardlens.companion;
import org.junit.Test;
import static org.junit.Assert.*;
public class BoardGeometryTest {
 @Test public void perspectiveRoundTripsAndBothOrientations(){BoardGeometry g=new BoardGeometry(140,70,650,85,760,690,25,670);for(double u:new double[]{0,.1,.5,.9,1})for(double v:new double[]{0,.1,.5,.9,1}){double[] p=g.map(u,v),q=g.unmap(p[0],p[1]);assertEquals(u,q[0],1e-8);assertEquals(v,q[1],1e-8);}assertArrayEquals(g.square("a1",true),g.square("h8",false),1e-8);assertTrue(g.cellWidth(7,0)>g.cellWidth(0,0));}
 @Test public void rectangularSquaresAreCentered(){BoardGeometry g=BoardGeometry.rectangle(10,30,810,830);assertArrayEquals(new double[]{60,780},g.square("a1",true),1e-8);assertArrayEquals(new double[]{460,480},g.square("e4",true),1e-8);}
 @Test(expected=IllegalArgumentException.class)public void rejectsCrossedCorners(){new BoardGeometry(0,0,100,100,100,0,0,100);}
 @Test(expected=IllegalArgumentException.class)public void rejectsDegenerate(){BoardGeometry.rectangle(0,0,0,100);}
}
