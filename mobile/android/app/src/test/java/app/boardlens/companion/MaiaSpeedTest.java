package app.boardlens.companion;

import android.app.Application;
import java.nio.file.*;
import java.util.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import static org.junit.Assert.*;

/** Optional real-model timing. Host times are not physical phone measurements. */
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
@android.annotation.TargetApi(35)
public class MaiaSpeedTest {
  @Test public void profileAllFourModelsAndRepeatedPositions()throws Exception {
    String models=System.getenv("BOARDLENS_MAIA_TEST_MODELS");Assume.assumeTrue(models!=null);
    var app=RuntimeEnvironment.getApplication();ChessPosition board=new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    try(MaiaLocal engine=new MaiaLocal()){
      for(String id:new String[]{"maia2","maia3-5m","maia3-23m","maia3-79m"}){
        Path target=PhoneModels.file(app,id).toPath();Files.deleteIfExists(target);Files.createLink(target,Path.of(models,id+".onnx"));
        app.getSharedPreferences("phone-model-files",0).edit().putString(id,PhoneModels.entry(app,id).getString("sha256")).commit();
        var countField=MaiaLocal.class.getDeclaredField("inferenceCount");countField.setAccessible(true);long before=countField.getLong(engine);
        long start=System.nanoTime();MaiaLocal.Prediction first=engine.search(app,board,id,1500,3,1);long cold=System.nanoTime()-start;
        double[] times=new double[7];for(int i=0;i<times.length;i++){
          long tick=System.nanoTime();MaiaLocal.Prediction repeat=engine.search(app,board,id,1500,1+i%3,1);times[i]=(System.nanoTime()-tick)/1e6;
          assertEquals(first.result().lines().get(0).move(),repeat.result().lines().get(0).move());assertEquals(1+i%3,repeat.result().lines().size());assertEquals(first.whiteExpected(),repeat.whiteExpected(),.00001f);
        }
        assertEquals("Repeats and different move counts must reuse the full ranking",before+1,countField.getLong(engine));
        Arrays.sort(times);System.out.printf(Locale.ROOT,"%s: cold %.2f ms; repeated position median %.3f ms%n",id,cold/1e6,times[times.length/2]);
      }
    }
  }
}
