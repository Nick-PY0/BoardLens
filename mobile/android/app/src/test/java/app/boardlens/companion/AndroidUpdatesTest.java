package app.boardlens.companion;
import android.app.Application;import org.json.*;import org.junit.*;import org.junit.runner.RunWith;import org.robolectric.*;import org.robolectric.annotation.*;import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
public class AndroidUpdatesTest {
 private JSONObject release()throws Exception{return new JSONObject("{\"html_url\":\"https://github.com/Nick-PY0/BoardLens/releases/tag/android-v1.7.0\",\"assets\":[{\"name\":\"BoardLens-Companion-Android.apk\",\"browser_download_url\":\"https://github.com/Nick-PY0/BoardLens/releases/download/android-v1.7.0/BoardLens-Companion-Android.apk\"},{\"name\":\"boardlens-update.json\",\"browser_download_url\":\"https://github.com/Nick-PY0/BoardLens/releases/download/android-v1.7.0/boardlens-update.json\"}]}");}
 @Test public void androidReleaseCanBeFoundIndependentlyOfDesktopLatest()throws Exception{assertTrue(AppUpdater.eligible(release()));assertFalse(AppUpdater.eligible(release().put("draft",true)));assertFalse(AppUpdater.eligible(release().put("prerelease",true)));}
 @Test public void modelOnlyAndForeignDownloadReleasesAreIgnored()throws Exception{JSONObject r=release();r.getJSONArray("assets").remove(0);assertFalse(AppUpdater.eligible(r));r=release();r.getJSONArray("assets").getJSONObject(1).put("browser_download_url","https://example.com/manifest.json");assertFalse(AppUpdater.eligible(r));}
}
