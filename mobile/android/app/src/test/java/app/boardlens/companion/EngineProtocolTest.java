package app.boardlens.companion;
import android.app.Application;import org.junit.*;import org.junit.runner.RunWith;import org.robolectric.*;import org.robolectric.annotation.*;import java.io.*;import java.lang.reflect.*;import java.util.*;import java.util.concurrent.*;import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class) @Config(sdk=35,application=Application.class)
public class EngineProtocolTest {
 private void set(Object target,String name,Object value)throws Exception{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);f.set(target,value);}
 @Test public void newPositionDrainsCancelledSearchBeforeNewGo()throws Exception{
  PhoneEngine engine=new PhoneEngine();Field q=PhoneEngine.class.getDeclaredField("output");q.setAccessible(true);BlockingQueue<String> output=(BlockingQueue<String>)q.get(engine);List<String> commands=new ArrayList<>();
  Process fake=new Process(){public OutputStream getOutputStream(){return OutputStream.nullOutputStream();}public InputStream getInputStream(){return InputStream.nullInputStream();}public InputStream getErrorStream(){return InputStream.nullInputStream();}public int waitFor(){return 0;}public int exitValue(){throw new IllegalThreadStateException();}public void destroy(){}public boolean isAlive(){return true;}};
  Writer writer=new Writer(){StringBuilder text=new StringBuilder();public void write(char[] c,int a,int n){text.append(c,a,n);}public void close(){}public void flush(){for(String command:text.toString().split("\n")){commands.add(command);if(command.equals("stop"))output.offer("bestmove e2e4");if(command.equals("isready"))output.offer("readyok");if(command.startsWith("go ")){output.offer("info depth 9 score cp 32 pv e7e5 g1f3");output.offer("bestmove e7e5");}}text.setLength(0);}};
  set(engine,"process",fake);set(engine,"input",new BufferedWriter(writer));set(engine,"searching",true);
  PhoneSettings settings=new PhoneSettings(RuntimeEnvironment.getApplication(),"protocol-test");settings.p.edit().clear().putFloat("seconds",.2f).apply();ChessPosition board=new ChessPosition("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1");PhoneEngine.Result result=engine.search(RuntimeEnvironment.getApplication(),board,settings,false,null);
  assertEquals("e7e5",result.lines().get(0).move());assertEquals(Integer.valueOf(-32),result.lines().get(0).cp());assertEquals("stop",commands.get(0));assertTrue(commands.contains("go movetime 200 depth 18"));assertTrue(commands.contains("setoption name Threads value 1"));
 }
}
