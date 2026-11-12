package app.boardlens.companion;
import android.app.*;
import android.content.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.util.*;

public final class ModelsActivity extends Activity {
 private MobileUi ui;private final Map<String,Button> buttons=new HashMap<>();private TextView state;private boolean checking;
 @Override public void onCreate(Bundle saved){super.onCreate(saved);ui=new MobileUi(this);ScrollView root=new ScrollView(this);root.setBackgroundColor(MobileUi.BG);LinearLayout col=ui.column();col.setPadding(ui.dp(20),ui.dp(12),ui.dp(20),ui.dp(24));root.addView(col);
  col.addView(ui.button("‹ Phone analysis",false,this::finish),new LinearLayout.LayoutParams(-1,ui.dp(48)));ui.gap(col,16);col.addView(ui.text("Engine library",26,MobileUi.FG,true));ui.gap(col,8);col.addView(ui.text("Everything runs on this phone. Download only the data models you want.",14,MobileUi.MUTED,false));ui.gap(col,14);
  state=ui.text("",14,MobileUi.ACCENT,false);col.addView(state);
  col.addView(ui.button("Download all models",true,()->download(new String[]{"stockfish","maia3-5m","maia3-23m","maia3-79m","maia2","lc0"})),new LinearLayout.LayoutParams(-1,ui.dp(50)));ui.gap(col,8);
  col.addView(ui.button("Cancel download",false,()->startService(new Intent(this,ModelDownloads.class).setAction("CANCEL"))),new LinearLayout.LayoutParams(-1,ui.dp(48)));ui.gap(col,18);
  col.addView(ui.button("Test installed engines",false,this::check),new LinearLayout.LayoutParams(-1,ui.dp(48)));ui.gap(col,18);
  for(EngineCatalog.Entry engine:EngineCatalog.ALL){LinearLayout card=ui.card();card.addView(ui.text(engine.name(),18,MobileUi.FG,true));ui.gap(card,6);card.addView(ui.text(engine.detail(),13,MobileUi.MUTED,false));ui.gap(card,12);
   if(engine.tiny()){card.addView(ui.text(TinyLocal.available()?"Built in · no download":"Requires the complete BoardLens APK",13,MobileUi.ACCENT,false));}
   else if(engine.id().equals("flounder")){card.addView(ui.text("Uses the Stockfish data above",13,MobileUi.MUTED,false));}
   else{Button b=ui.button("",false,()->download(new String[]{engine.id()}));buttons.put(engine.id(),b);card.addView(b,new LinearLayout.LayoutParams(-1,ui.dp(48)));}
   col.addView(card);ui.gap(col,12);
  }
  col.addView(ui.text("Tiny ratings are the original competition results, not a promised phone playing strength. Models keep working offline after download.",13,MobileUi.MUTED,false));
  MobileUi.inset(this,root);setContentView(root);refresh();
 }
 private void check(){if(checking)return;if(ScreenService.running){Toast.makeText(this,"Stop screen analysis before running engine checks",Toast.LENGTH_LONG).show();return;}checking=true;state.setText("Checking installed engines…");EngineCheck.run(this,text->runOnUiThread(()->{if(!isFinishing()&&!isDestroyed())state.setText(text);}),result->runOnUiThread(()->{checking=false;if(!isFinishing()&&!isDestroyed()){state.setText("Engine check complete");new AlertDialog.Builder(this).setTitle("Engine check").setMessage(result).setPositiveButton("Done",null).show();}}));}
 private void download(String[] models){ArrayList<String> ids=new ArrayList<>();for(String id:models)if(!EngineCatalog.ready(this,id))ids.add(id);if(ids.isEmpty()){Toast.makeText(this,"Already installed",Toast.LENGTH_SHORT).show();return;}startForegroundService(new Intent(this,ModelDownloads.class).putStringArrayListExtra("models",ids));}
 private void refresh(){if(isFinishing())return;state.setText(ModelDownloads.message);for(var entry:buttons.entrySet()){boolean ready=EngineCatalog.ready(this,entry.getKey());Button b=entry.getValue();b.setText(ready?"Installed":ModelDownloads.current.equals(entry.getKey())?"Downloading · "+ModelDownloads.progress+"%":"Download · "+(entry.getKey().equals("stockfish")?"99 MB":PhoneModels.size(this,entry.getKey())));b.setEnabled(!ready&&!ModelDownloads.current.equals(entry.getKey()));}}
 @Override public void onResume(){super.onResume();ModelDownloads.listener=this::refresh;refresh();}
 @Override public void onPause(){ModelDownloads.listener=null;super.onPause();}
  @Override protected void onStart(){super.onStart();PhoneUiVisibility.start(this);}
  @Override protected void onStop(){PhoneUiVisibility.stop(this);super.onStop();}

}
