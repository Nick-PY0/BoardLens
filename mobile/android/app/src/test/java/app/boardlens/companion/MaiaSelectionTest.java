package app.boardlens.companion;
import android.app.Application;import android.widget.Button;import org.junit.*;import org.junit.runner.RunWith;import org.robolectric.*;import org.robolectric.annotation.*;import java.nio.file.*;import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class) @android.annotation.TargetApi(35)
public class MaiaSelectionTest {
 @Test public void downloadedModelHasExplicitSelectionWithoutChangingEvaluation()throws Exception{
  String root=System.getenv("BOARDLENS_MAIA_TEST_MODELS");Assume.assumeTrue(root!=null);var app=RuntimeEnvironment.getApplication();Path file=PhoneModels.file(app,"maia3-5m").toPath();Files.deleteIfExists(file);Files.createLink(file,Path.of(root,"maia3-5m.onnx"));app.getSharedPreferences("phone-model-files",0).edit().putString("maia3-5m",PhoneModels.entry(app,"maia3-5m").getString("sha256")).commit();PhoneSettings prefs=new PhoneSettings(app);prefs.p.edit().clear().putString("engine","stockfish").putString("evaluator","stockfish").commit();
  var controller=Robolectric.buildActivity(ModelsActivity.class).setup();ModelsActivity a=controller.get();Button choose=a.findViewById(android.R.id.content).findViewWithTag("model-maia3-5m");assertEquals("Use for moves",choose.getText().toString());choose.performClick();assertEquals("maia3-5m",prefs.engine());assertEquals("stockfish",prefs.evaluator());controller.pause().stop().destroy();
 }
}
