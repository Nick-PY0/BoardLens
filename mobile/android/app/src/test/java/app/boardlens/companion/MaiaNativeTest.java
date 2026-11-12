package app.boardlens.companion;
import android.app.Application;import org.json.*;import org.junit.*;import org.junit.runner.RunWith;import org.robolectric.*;import org.robolectric.annotation.*;import java.io.*;import java.nio.file.*;import static org.junit.Assert.*;
/** Runs the production Java adapter with the same ORT version and real exported weights. */
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class) @android.annotation.TargetApi(35)
public class MaiaNativeTest {
 @Test public void realMaiaModelsRankReferencePositionsThroughProductionAdapter()throws Exception{
  String root=System.getenv("BOARDLENS_MAIA_TEST_MODELS");Assume.assumeTrue("Optional real model files are needed",root!=null);var app=RuntimeEnvironment.getApplication();
  try(MaiaLocal engine=new MaiaLocal()){
   for(String id:new String[]{"maia2","maia3-5m","maia3-23m","maia3-79m"}){
    Path source=Path.of(root,id+".onnx"),dest=PhoneModels.file(app,id).toPath();Files.deleteIfExists(dest);Files.createLink(dest,source);app.getSharedPreferences("phone-model-files",0).edit().putString(id,PhoneModels.entry(app,id).getString("sha256")).commit();
    JSONArray fixtures;try(InputStream in=getClass().getClassLoader().getResourceAsStream("maia/"+id+"-golden.json")){fixtures=new JSONArray(new String(in.readAllBytes(),java.nio.charset.StandardCharsets.UTF_8));}
    for(int i=0;i<fixtures.length();i++){
     JSONObject fixture=fixtures.getJSONObject(i);ChessPosition board=new ChessPosition(fixture.getString("fen"));MaiaLocal.Prediction result=engine.search(app,board,id,fixture.getInt("rating"),3,1);
     assertFalse(id,result.result().lines().isEmpty());assertEquals(id+" "+board.fen(),fixture.getString("best_move"),result.result().lines().get(0).move());assertTrue(result.whiteExpected()>=0&&result.whiteExpected()<=1);
    }
    System.out.println(id+" production Java/native inference: "+fixtures.length()+" positions passed");
   }
  }
 }
}
