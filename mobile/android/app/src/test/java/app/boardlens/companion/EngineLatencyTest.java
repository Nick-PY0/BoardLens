package app.boardlens.companion;

import android.app.Application;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
public class EngineLatencyTest {
  private static final String START="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
  private void set(Object target,String name,Object value)throws Exception {Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);f.set(target,value);}
  private Object get(Object target,String name)throws Exception {Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(target);}
  private final List<String> commands=new CopyOnWriteArrayList<>();
  private BlockingQueue<String> install(PhoneEngine engine,java.util.function.Consumer<String> command)throws Exception {
    Process fake=new Process(){public OutputStream getOutputStream(){return OutputStream.nullOutputStream();}public InputStream getInputStream(){return InputStream.nullInputStream();}public InputStream getErrorStream(){return InputStream.nullInputStream();}public int waitFor(){return 0;}public int exitValue(){throw new IllegalThreadStateException();}public void destroy(){}public boolean isAlive(){return true;}};
    BlockingQueue<String> output=(BlockingQueue<String>)get(engine,"output");
    Writer writer=new Writer(){StringBuilder text=new StringBuilder();public void write(char[] c,int a,int n){text.append(c,a,n);}public void close(){}public void flush(){for(String line:text.toString().split("\n")){commands.add(line);if(line.equals("isready"))output.offer("readyok");command.accept(line);}text.setLength(0);}};
    set(engine,"process",fake);set(engine,"input",new BufferedWriter(writer));return output;
  }
  @Test public void firstDepthStreamsWithoutReducingTheChosenTime()throws Exception {
    PhoneEngine engine=new PhoneEngine();BlockingQueue<String>[] out=new BlockingQueue[1];
    out[0]=install(engine,line->{if(line.startsWith("go "))out[0].offer("info depth 1 score cp 18 pv e2e4");});
    PhoneSettings prefs=new PhoneSettings(RuntimeEnvironment.getApplication(),"latency-time");prefs.p.edit().clear().putString("mode","Time").putFloat("seconds",3f).apply();
    CountDownLatch early=new CountDownLatch(1);ExecutorService worker=Executors.newSingleThreadExecutor();
    try {
      Future<PhoneEngine.Result> search=worker.submit(()->engine.search(RuntimeEnvironment.getApplication(),new ChessPosition(START),prefs,false,r->early.countDown()));
      assertTrue("First legal depth must stream before bestmove",early.await(3,TimeUnit.SECONDS));
      assertFalse(search.isDone());assertTrue(commands.contains("go movetime 3000"));assertFalse(commands.contains("stop"));
      out[0].offer("bestmove e2e4");assertEquals("e2e4",search.get(3,TimeUnit.SECONDS).lines().get(0).move());
      engine.search(RuntimeEnvironment.getApplication(),new ChessPosition(START),prefs,false,r->{out[0].offer("bestmove e2e4");});
      assertEquals("Warm positions skip redundant ready handshakes",1,Collections.frequency(commands,"isready"));
    } finally {engine.close();worker.shutdownNow();}
  }
  @Test public void completedRootPublishesBeforeReplySearchWithEarlyOff()throws Exception {
    LocalEngines engines=new LocalEngines();PhoneEngine engine=(PhoneEngine)get(engines,"stockfish");
    BlockingQueue<String>[] out=new BlockingQueue[1];int[] searches={0};CountDownLatch replyStarted=new CountDownLatch(1);
    out[0]=install(engine,line->{if(line.startsWith("go ")){
      if(++searches[0]==1){out[0].offer("info depth 1 score cp 18 pv e2e4");out[0].offer("bestmove e2e4");}
      else if(searches[0]==2)replyStarted.countDown();
      else {out[0].offer("info depth 5 score cp 20 pv g1f3");out[0].offer("bestmove g1f3");}
    }});
    PhoneSettings prefs=new PhoneSettings(RuntimeEnvironment.getApplication(),"latency-replies");prefs.p.edit().clear().putBoolean("early",false).putInt("prediction_plies",3).apply();
    CountDownLatch rootVisible=new CountDownLatch(1);ExecutorService worker=Executors.newSingleThreadExecutor();
    try {
      Future<PhoneEngine.Result> search=worker.submit(()->engines.recommend(RuntimeEnvironment.getApplication(),new ChessPosition(START),prefs,()->true,(result,rootComplete)->{
        if(rootComplete||prefs.early()){assertEquals("e2e4",result.lines().get(0).move());rootVisible.countDown();}
      }));
      assertTrue(rootVisible.await(3,TimeUnit.SECONDS));assertTrue(replyStarted.await(3,TimeUnit.SECONDS));
      assertFalse("Slow optional replies must not block the completed root",search.isDone());
      out[0].offer("info depth 4 score cp -12 pv e7e5");out[0].offer("bestmove e7e5");
      assertEquals(Arrays.asList("e2e4","e7e5","g1f3"),search.get(3,TimeUnit.SECONDS).lines().get(0).pv());
    } finally {engines.close();worker.shutdownNow();}
  }
}
