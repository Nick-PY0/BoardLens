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

/** Optional host benchmark of the production UCI parser with real Stockfish. */
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
public class NativeEngineLatencyTest {
  private void set(Object o,String name,Object value)throws Exception{Field f=PhoneEngine.class.getDeclaredField(name);f.setAccessible(true);f.set(o,value);}
  @Test public void realEngineShowsLegalMovesBeforeItsFullTimeBudget()throws Exception {
    String path=System.getenv("BOARDLENS_STOCKFISH_TEST_ENGINE");Assume.assumeTrue(path!=null);
    PhoneEngine engine=new PhoneEngine();Process nativeEngine=new ProcessBuilder(path).redirectErrorStream(true).start();
    BufferedWriter input=new BufferedWriter(new OutputStreamWriter(nativeEngine.getOutputStream()));
    Field f=PhoneEngine.class.getDeclaredField("output");f.setAccessible(true);BlockingQueue<String> output=(BlockingQueue<String>)f.get(engine);
    Thread reader=new Thread(()->{try(BufferedReader in=new BufferedReader(new InputStreamReader(nativeEngine.getInputStream()))){String line;while((line=in.readLine())!=null)output.offer(line);}catch(IOException ignored){}});reader.setDaemon(true);reader.start();
    set(engine,"process",nativeEngine);set(engine,"input",input);
    input.write("uci\n");input.flush();long limit=System.nanoTime()+TimeUnit.SECONDS.toNanos(10);
    for(;;){String line=output.poll(1,TimeUnit.SECONDS);if("uciok".equals(line))break;assertTrue("UCI initialization",System.nanoTime()<limit);}
    PhoneSettings prefs=new PhoneSettings(RuntimeEnvironment.getApplication(),"native-latency");prefs.p.edit().clear().putString("mode","Time").putFloat("seconds",.5f).putBoolean("predict",false).apply();
    ChessPosition board=new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    try {
      engine.prepare(RuntimeEnvironment.getApplication(),"stockfish",prefs,false);
      for(String played:new String[]{"e2e4","e7e5","g1f3","b8c6","f1b5","a7a6"}){
        long start=System.nanoTime();long[] first={0};ChessPosition current=board;
        PhoneEngine.Result result=engine.search(RuntimeEnvironment.getApplication(),board,prefs,false,r->{assertTrue(current.legal().contains(r.lines().get(0).move()));if(first[0]==0)first[0]=System.nanoTime();});
        long end=System.nanoTime();assertTrue(first[0]>start&&first[0]<end);assertTrue(board.legal().contains(result.lines().get(0).move()));
        System.out.printf(Locale.ROOT,"Real Stockfish / production adapter: first %.1f ms; completed %.1f ms; budget %.1f s%n",(first[0]-start)/1e6,(end-start)/1e6,prefs.seconds());board=board.play(played);
      }
    } finally {engine.close();}
  }
}
