package app.boardlens.companion;
import android.content.Context;
import java.util.*;
import java.util.function.Consumer;

/** User-run device check: real inference and legal-move validation, without screen access. */
final class EngineCheck {
 static void run(Context context,Consumer<String> update,Consumer<String> done){
  new Thread(()->{StringBuilder report=new StringBuilder();Context c=context.getApplicationContext();
   PhoneSettings test=new PhoneSettings(c,"engine-check");test.p.edit().putFloat("seconds",1f).putString("mode","Time").putInt("moves",1).putInt("threads",1).putBoolean("predict",false).apply();
   ChessPosition board=new ChessPosition("r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1");
   int ok=0,failed=0,skipped=0;
   try(LocalEngines engines=new LocalEngines()){
    for(var entry:EngineCatalog.ALL){if(!EngineCatalog.ready(c,entry.id())){skipped++;continue;}update.accept("Checking "+entry.name()+"…");test.p.edit().putString("engine",entry.id()).apply();
     try{PhoneEngine.Result result=engines.recommend(c,board,test,()->true,null);if(result.lines().isEmpty()||!board.legal().contains(result.lines().get(0).move()))throw new java.io.IOException("No legal move returned");report.append("✓ ").append(entry.name()).append(" · ").append(result.lines().get(0).move()).append('\n');ok++;}
     catch(Exception error){report.append("! ").append(entry.name()).append(" · ").append(error.getMessage()).append('\n');failed++;}
    }
   }catch(Exception error){report.append("Check stopped: ").append(error.getMessage());failed++;}
   String text=ok+" passed · "+failed+" failed · "+skipped+" not installed\n\n"+report+"\nThis checks engine execution, not live screen recognition.";c.getSharedPreferences("engine-check",0).edit().putString("lastResult",text).apply();done.accept(text);
  },"BoardLens-engine-check").start();
 }
}
