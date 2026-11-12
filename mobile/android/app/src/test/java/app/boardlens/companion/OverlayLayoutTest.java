package app.boardlens.companion;
import org.junit.Test;import static org.junit.Assert.*;
public class OverlayLayoutTest {
 @Test public void portraitBarFitsAboveBoardAndBelowCutout(){var b=OverlayLayout.place(new double[]{0,150,360,510},360,800,1,28,24,"Auto");assertTrue(b.top()>=36);assertTrue(b.bottom()<150);assertTrue(b.left()>=0&&b.right()<=360);assertFalse(b.vertical());}
 @Test public void landscapeUsesFreeSpaceBesideBoard(){var b=OverlayLayout.place(new double[]{170,35,690,555},960,600,1,24,24,"Auto");assertTrue(b.vertical());assertTrue(b.right()<170);assertTrue(b.bottom()<=576);}
 @Test public void explicitPlacementsStayInsideSafeDisplay(){for(String mode:new String[]{"Top","Bottom","Left","Right"}){var b=OverlayLayout.place(new double[]{0,32,360,392},360,800,1,32,28,mode);assertTrue(b.top()>=40);assertTrue(b.bottom()<=772);assertTrue(b.left()>=0);assertTrue(b.right()<=360);}}
}
