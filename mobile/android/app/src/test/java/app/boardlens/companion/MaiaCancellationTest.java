package app.boardlens.companion;
import ai.onnxruntime.*;
import android.app.Application;
import java.lang.reflect.*;
import java.util.concurrent.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
public class MaiaCancellationTest {
 static final class PausedOptions extends OrtSession.RunOptions {
  final CountDownLatch cancelling=new CountDownLatch(1),release=new CountDownLatch(1);
  PausedOptions()throws OrtException{}
  @Override public void setTerminate(boolean value)throws OrtException{
   cancelling.countDown();try{if(!release.await(5,TimeUnit.SECONDS))throw new AssertionError("cancel test timed out");}catch(InterruptedException e){throw new AssertionError(e);}
   super.setTerminate(value);
  }
 }
 @Test public void nativeOptionsCannotCloseWhileCancellationBorrowsThem()throws Exception{
  MaiaLocal model=new MaiaLocal();PausedOptions options=new PausedOptions();Field active=MaiaLocal.class.getDeclaredField("active");active.setAccessible(true);active.set(model,options);
  Method end=MaiaLocal.class.getDeclaredMethod("endRun",OrtSession.RunOptions.class);end.setAccessible(true);ExecutorService threads=Executors.newFixedThreadPool(2);
  try{
   Future<?> cancelling=threads.submit(model::cancel);assertTrue(options.cancelling.await(3,TimeUnit.SECONDS));CountDownLatch retiring=new CountDownLatch(1);
   Future<?> disposing=threads.submit(()->{retiring.countDown();try{end.invoke(model,options);}catch(Exception e){throw new AssertionError(e);}});
   assertTrue(retiring.await(3,TimeUnit.SECONDS));assertFalse(disposing.isDone());options.release.countDown();cancelling.get(3,TimeUnit.SECONDS);disposing.get(3,TimeUnit.SECONDS);assertNull(active.get(model));model.cancel();
  }finally{options.release.countDown();threads.shutdownNow();model.close();}
 }
}
