package app.boardlens.companion;
import android.app.Application;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
public class SettingsSnapshotTest {
 @Test public void activeSearchKeepsItsOriginalEngineAndBudgets(){
  PhoneSettings live=new PhoneSettings(RuntimeEnvironment.getApplication(),"snapshot-test");live.p.edit().clear().putString("engine","tiny614").putBoolean("evaluation_enabled",false).putFloat("seconds",.3f).putInt("depth",12).commit();PhoneSettings active=live.snapshot();
  live.p.edit().putString("engine","maia3-79m").putBoolean("evaluation_enabled",true).putFloat("seconds",2f).putInt("depth",20).commit();
  assertEquals("tiny614",active.engine());assertFalse(active.evaluationEnabled());assertEquals(.3f,active.seconds(),.001);assertEquals(12,active.depth());assertEquals("maia3-79m",live.engine());assertEquals(20,live.depth());
 }
 @Test public void crashDiagnosticsKeepFramesAndSecretsOut(){
  var app=RuntimeEnvironment.getApplication();Diagnostics.record(app,new IllegalStateException("private-position-or-pairing-key"));String report=Diagnostics.report(app);
  assertTrue(report.contains("IllegalStateException"));assertFalse(report.contains("private-position-or-pairing-key"));assertTrue(report.contains("Engine at crash"));
  assertTrue(report.contains("Scanner stage:"));assertTrue(report.contains("Captured frames:"));assertTrue(report.contains("Capture size:"));
 }
}
