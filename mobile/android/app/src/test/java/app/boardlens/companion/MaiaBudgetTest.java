package app.boardlens.companion;

import android.app.Application;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import static org.junit.Assert.*;

/** Real inference plus a controlled monotonic clock, without timing-sensitive assertions. */
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
@android.annotation.TargetApi(35)
public class MaiaBudgetTest {
  private final ChessPosition board=new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
  private Object get(Object target,String name)throws Exception{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(target);}
  private void install()throws Exception{
    String models=System.getenv("BOARDLENS_MAIA_TEST_MODELS");Assume.assumeTrue(models!=null);var app=RuntimeEnvironment.getApplication();Path target=PhoneModels.file(app,"maia3-5m").toPath();Files.deleteIfExists(target);Files.createLink(target,Path.of(models,"maia3-5m.onnx"));
    app.getSharedPreferences("phone-model-files",0).edit().putString("maia3-5m",PhoneModels.entry(app,"maia3-5m").getString("sha256")).commit();
  }
  @Test public void timeBudgetStopsExtraPassesButAlwaysPublishesFirstMoveAndReusesPredictions()throws Exception{
    install();var app=RuntimeEnvironment.getApplication();PhoneSettings settings=new PhoneSettings(app,"maia-budget");settings.p.edit().clear().putString("engine","maia3-5m").putFloat("seconds",.05f).putFloat("prediction_seconds",30f).apply();
    AtomicLong clock=new AtomicLong();AtomicBoolean firstPublished=new AtomicBoolean();
    try(LocalEngines engines=new LocalEngines(clock::get)){
      engines.prepare(app,settings,false);MaiaLocal model=(MaiaLocal)get(engines,"maia");assertNotNull(get(model,"session"));assertEquals(0L,get(model,"inferenceCount"));
      PhoneEngine.Result root=engines.recommend(app,board,settings,()->true,(r,complete)->{if(complete){firstPublished.set(true);clock.set(1_000_000_000L);}});
      assertTrue(firstPublished.get());assertEquals(1,root.lines().get(0).pv().size());assertEquals(1L,get(model,"inferenceCount"));
      settings.p.edit().putFloat("seconds",3f).apply();clock.set(0);
      PhoneEngine.Result full=engines.recommend(app,board,settings,()->true,(r,complete)->clock.addAndGet(100_000_000L));
      assertEquals(3,full.lines().get(0).pv().size());assertEquals(3L,get(model,"inferenceCount"));
      settings.p.edit().putBoolean("predict",false).apply();ChessPosition actual=board.play(full.lines().get(0).move());
      PhoneEngine.Result next=engines.recommend(app,actual,settings,()->true,null);
      assertEquals(full.lines().get(0).pv().get(1),next.lines().get(0).move());assertEquals("Actual predicted board reuses its completed inference",3L,get(model,"inferenceCount"));
      settings.p.edit().putInt("rating",1800).apply();engines.recommend(app,actual,settings,()->true,null);assertEquals("A new rating must not reuse the old policy",4L,get(model,"inferenceCount"));
    }
  }
  @Test public void predictionCacheIsBoundedAndReleasedWhenClosed()throws Exception{
    install();var app=RuntimeEnvironment.getApplication();MaiaLocal model=new MaiaLocal();
    try {
      for(int i=0;i<70;i++)model.search(app,new ChessPosition(board.placement()+" w KQkq - "+i+" 1"),"maia3-5m",1500,1,1);
      assertEquals(64,((Map<?,?>)get(model,"cache")).size());assertEquals(70L,get(model,"inferenceCount"));
    }finally{model.close();}
    assertEquals(0,((Map<?,?>)get(model,"cache")).size());assertNull(get(model,"session"));
  }
}
