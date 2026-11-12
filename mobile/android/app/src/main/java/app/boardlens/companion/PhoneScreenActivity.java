package app.boardlens.companion;

import android.app.*;
import android.content.*;
import android.media.projection.*;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.widget.*;
import java.util.*;

/** The phone-analysis section of the companion; every recommendation runs on-device. */
public class PhoneScreenActivity extends Activity {
 private PhoneSettings settings;private MobileUi ui;private PhoneDashboard dashboard;
 private LinearLayout content;private boolean settingsPage,pendingOverlay;
 private final Map<String,View> controls=new HashMap<>();private TextView modelNote;
 @Override public void onCreate(Bundle saved){super.onCreate(saved);settings=new PhoneSettings(this);ui=new MobileUi(this);pendingOverlay=saved!=null&&saved.getBoolean("overlay");getWindow().setStatusBarColor(MobileUi.BG);getWindow().setNavigationBarColor(MobileUi.BG);if(Build.VERSION.SDK_INT>=33)getOnBackInvokedDispatcher().registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,this::goBack);show();}
 private void show(){settingsPage=false;dashboard=new PhoneDashboard(this,new PhoneDashboard.Actions(){
  public void start(){PhoneScreenActivity.this.start();}public void stop(){stopService(new Intent(PhoneScreenActivity.this,ScreenService.class));}public void hide(){moveTaskToBack(true);}
  public void scan(){if(ScreenService.running)startService(new Intent(PhoneScreenActivity.this,ScreenService.class).setAction("REFRESH"));else PhoneScreenActivity.this.start();}
  public void settings(){engineSettings();}public void help(){showHelp();}public void back(){finish();}
  public boolean option(String key,boolean fallback){return settings.p.getBoolean(key,fallback);}public void option(String key,boolean value,boolean unused){settings.p.edit().putBoolean(key,value).apply();}
 });MobileUi.inset(this,dashboard.root);setContentView(dashboard.root);refresh();}
 private void showHelp(){
  String[] sections={"Start & background scanning","Engines & downloads","Thinking & predictions","Arrows & your color","Permissions & troubleshooting"};
  String[] help={
   "Press Start, approve sharing your entire screen, then press Home or Open another app. BoardLens keeps scanning while its foreground-service notification is present, even when its interface is closed. Stop in the app or notification ends the session. Keep all 64 squares visible. Reading pauses on BoardLens’s own screens to avoid reading its preview.",
   "All phone-screen engines run on this device. Stockfish and Flounder share the Stockfish data file. Maia 2 and Maia 3 5M/23M/79M are optional data-model downloads. Original Tiny bots are built into the complete APK. Competition ratings are reference results, not guaranteed phone ratings. The Computer companion section remains available for controlling desktop boards, but is not needed for phone analysis. Downloads are checksum-verified and keep working offline. Recommendation and evaluation engines are independent. Maia evaluation is a human expected score, not Stockfish centipawns or a win probability.",
   "Stockfish accepts time, depth, or whichever limit is reached first. Flounder uses Stockfish with an Elo limit. Tiny bots control their own depth; think time supplies their clock budget. Maia predicts in one neural pass, so it has no native search-depth control. Maia 2 uses rating buckets from below 1100 to 2000 and above; Maia 3 accepts a wider target rating. Show moves while thinking shows early results. Predict replies extends the chosen engine’s line. Three plies means your move, an opponent reply, then your response. Reply budget limits additional model passes; a running pass may finish after the budget.",
   "Screen arrows pass taps through to the chess app. Only my color uses the side at the bottom of the recognized board. Steady arrows reduces changes during thinking. Lock move keeps the first displayed suggestion for the position while evaluation continues. A board change, settings change or Scan now releases the lock. Tiny bots provide one recommendation per search. Other engines support multiple alternatives. Predictions describe a possible continuation, not a promise that the opponent will choose it.",
   "Android asks for screen-sharing approval for each new capture session. Display over other apps is needed only for arrows and stays allowed until revoked. No Accessibility service is used. Android may stop sharing when you lock the device, revoke access or force-stop the app. Protected screens cannot be read. Scan now discards the current target and starts a fresh search. Unusual themes, hidden pieces and unsupported 3D camera angles can remain unreadable. Settings save automatically."
  };
  new AlertDialog.Builder(this).setTitle("Phone analysis help").setItems(sections,(d,which)->new AlertDialog.Builder(this).setTitle(sections[which]).setMessage(help[which]).setPositiveButton("Got it",null).show()).setNegativeButton("Close",null).show();
 }
 private void group(LinearLayout root,String title){ui.gap(root,14);content=ui.card();content.addView(ui.text(title,18,MobileUi.FG,true));ui.gap(content,12);root.addView(content);}
 private void choice(String title,String key,String[] labels,int selected,java.util.function.IntConsumer save){View row=ui.choice(title,labels,selected,index->{save.accept(index);refreshLimits();});controls.put(key,row);content.addView(row);ui.gap(content,10);}
 private void engine(String title,String key,boolean evaluation){List<EngineCatalog.Entry> list=new ArrayList<>();for(var entry:EngineCatalog.ALL)if(!evaluation||!entry.tiny())list.add(entry);String current=evaluation?settings.evaluator():settings.engine();String[] names=new String[list.size()];int selected=0;for(int i=0;i<list.size();i++){var e=list.get(i);names[i]=e.name()+(EngineCatalog.ready(this,e.id())?"":" · download");if(e.id().equals(current)||current.equals("maia3")&&e.id().equals("maia3-5m"))selected=i;}
  choice(title,key,names,selected,i->settings.p.edit().putString(key,list.get(i).id()).apply());
 }
 private void number(String title,String key,int min,int max,int value){LinearLayout row=ui.column();row.addView(ui.text(title,14,MobileUi.MUTED,false));ui.gap(row,6);row.addView(new MobileUi.Stepper(ui,min,max,value,key.equals("rating")?50:1,n->settings.p.edit().putInt(key,n).apply()),new LinearLayout.LayoutParams(-1,ui.dp(48)));controls.put(key,row);content.addView(row);ui.gap(content,12);}
 private void seconds(String title,String key,float value,float low,float high){LinearLayout row=ui.column();row.addView(ui.text(title,14,MobileUi.MUTED,false));EditText field=new EditText(this);field.setSingleLine();field.setTextColor(MobileUi.FG);field.setInputType(8194);field.setText(String.valueOf(value));field.setPadding(ui.dp(12),0,ui.dp(12),0);field.setBackground(ui.shape(MobileUi.BORDER,12));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,ui.dp(48));p.topMargin=ui.dp(6);row.addView(field,p);controls.put(key,row);content.addView(row);ui.gap(content,12);
  field.addTextChangedListener(new android.text.TextWatcher(){public void beforeTextChanged(CharSequence s,int a,int b,int c){}public void afterTextChanged(android.text.Editable s){}public void onTextChanged(CharSequence s,int a,int b,int c){try{float n=Float.parseFloat(s.toString());if(!Float.isFinite(n)||n<low||n>high)throw new Exception();settings.p.edit().putFloat(key,n).apply();field.setError(null);}catch(Exception e){field.setError(low+" to "+high+" seconds");}}});
 }
 private void toggle(String title,String detail,String key,boolean fallback){content.addView(ui.toggle(title,detail,settings.p.getBoolean(key,fallback),value->{settings.p.edit().putBoolean(key,value).apply();refreshLimits();}));}
 private void engineSettings(){settingsPage=true;controls.clear();ScrollView scroll=new ScrollView(this);scroll.setBackgroundColor(MobileUi.BG);LinearLayout root=ui.column();root.setPadding(ui.dp(20),ui.dp(12),ui.dp(20),ui.dp(24));scroll.addView(root);root.addView(ui.button("‹ Phone screen",false,this::show),new LinearLayout.LayoutParams(-1,ui.dp(48)));ui.gap(root,16);root.addView(ui.text("Phone settings",26,MobileUi.FG,true));
  group(root,"Engines");engine("Recommend moves","engine",false);engine("Evaluation bar","evaluator",true);content.addView(ui.button("Models & downloads",false,()->startActivity(new Intent(this,ModelsActivity.class))),new LinearLayout.LayoutParams(-1,ui.dp(48)));ui.gap(content,8);modelNote=ui.text("",13,MobileUi.MUTED,false);content.addView(modelNote);
  group(root,"Thinking");String[] modes={"Time","Depth","Time + depth"};choice("Stop at","mode",modes,Arrays.asList(modes).indexOf(settings.mode()),i->settings.p.edit().putString("mode",modes[i]).apply());seconds("Think time","seconds",settings.seconds(),.05f,30f);number("Search depth","depth",1,30,settings.depth());number("Target rating","rating",600,2600,settings.rating());number("Stockfish skill","skill",0,20,settings.skill());number("CPU threads","threads",1,Math.max(1,Math.min(8,Runtime.getRuntime().availableProcessors())),settings.threads());
  group(root,"Suggestions");number("Recommended moves","moves",1,5,settings.moves());toggle("Show moves while thinking","Show the first result early","early",true);toggle("Predict replies","Opponent move, then your response","predict",true);number("Prediction length · plies","prediction_plies",1,12,settings.predictionPlies());seconds("Reply time budget","prediction_seconds",settings.predictionSeconds(),.1f,60f);toggle("Steady arrows","Reduce changes during thinking","steady",true);toggle("Lock move","Keep the first suggestion for this position","lock_move",false);
  group(root,"Board & arrows");toggle("Screen arrows","Draw over the chess app","arrows",true);toggle("Only my color","Use the side at the bottom","onlyMine",false);String[] orientation={"Auto","White at bottom","Black at bottom"},turn={"Auto","White","Black"};choice("Orientation","orientation",orientation,Arrays.asList(orientation).indexOf(settings.orientation()),i->settings.p.edit().putString("orientation",orientation[i]).apply());choice("Side to move","turn",turn,Arrays.asList(turn).indexOf(settings.turn()),i->settings.p.edit().putString("turn",turn[i]).apply());
  ui.gap(root,16);root.addView(ui.text("Saved automatically",13,MobileUi.MUTED,false));ui.gap(root,8);root.addView(ui.button("Help",false,this::showHelp),new LinearLayout.LayoutParams(-1,ui.dp(48)));MobileUi.inset(this,scroll);setContentView(scroll);refreshLimits();
 }
 private void refreshLimits(){EngineCatalog.Entry e=EngineCatalog.get(settings.engine());boolean search=!e.maia()&&!e.tiny();visible("mode",search);visible("depth",search&&!settings.mode().equals("Time"));visible("seconds",!e.maia()&&(e.tiny()||!settings.mode().equals("Depth")));visible("rating",e.maia()||e.id().equals("flounder"));visible("skill",e.id().equals("stockfish"));visible("threads",!e.tiny());visible("moves",!e.tiny());visible("prediction_plies",settings.predict());visible("prediction_seconds",settings.predict());if(modelNote!=null)modelNote.setText(e.maia()?"One neural pass per position. Prediction length controls later moves.":e.tiny()?"Original bot · one move per search · its depth is automatic.":"Recommendations and evaluation run separately on this phone.");}
 private void visible(String key,boolean show){View view=controls.get(key);if(view!=null)view.setVisibility(show?View.VISIBLE:View.GONE);}
 private void start(){
  if(ScreenService.running){moveTaskToBack(true);return;}
  if(Build.VERSION.SDK_INT<29){new AlertDialog.Builder(this).setMessage("Phone screen analysis requires Android 10 or later. Computer companion still works here.").setPositiveButton("OK",null).show();return;}
  if(!EngineCatalog.ready(this,settings.engine())){Toast.makeText(this,"Install "+EngineCatalog.get(settings.engine()).name()+" first",Toast.LENGTH_LONG).show();startActivity(new Intent(this,ModelsActivity.class));return;}
  if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED&&!settings.p.getBoolean("notificationAsked",false)){settings.p.edit().putBoolean("notificationAsked",true).apply();requestPermissions(new String[]{android.Manifest.permission.POST_NOTIFICATIONS},9);return;}
  if(settings.arrows()&&!Settings.canDrawOverlays(this)){
   new AlertDialog.Builder(this).setTitle("Allow screen arrows").setMessage("Enable Display over other apps for BoardLens. Arrows let taps pass through to the chessboard.").setNegativeButton("Without arrows",(d,w)->{settings.p.edit().putBoolean("arrows",false).apply();requestCapture();}).setPositiveButton("Open settings",(d,w)->{pendingOverlay=true;startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+getPackageName())));}).show();return;
  }requestCapture();
 }
 private void requestCapture(){MediaProjectionManager manager=getSystemService(MediaProjectionManager.class);Intent consent=Build.VERSION.SDK_INT>=34?manager.createScreenCaptureIntent(MediaProjectionConfig.createConfigForDefaultDisplay()):manager.createScreenCaptureIntent();startActivityForResult(consent,42);}
 @Override public void onRequestPermissionsResult(int request,String[] names,int[] results){super.onRequestPermissionsResult(request,names,results);if(request==9)start();}
 @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request==42&&result==RESULT_OK&&data!=null){startForegroundService(new Intent(this,ScreenService.class).putExtra("consent",data));moveTaskToBack(true);}else if(request==42)Toast.makeText(this,"Screen sharing was not started",Toast.LENGTH_SHORT).show();}
 private void refresh(){if(!isFinishing()&&!settingsPage&&dashboard!=null){dashboard.engine.setText(EngineCatalog.get(settings.engine()).name()+" · on this phone");dashboard.render(ScreenService.running,ScreenService.status,ScreenService.suggestion,ScreenService.evaluation,ScreenService.whiteShare,ScreenService.preview);}}
 @Override protected void onStart(){super.onStart();PhoneUiVisibility.start(this);}
 @Override protected void onStop(){PhoneUiVisibility.stop(this);super.onStop();}
 @Override protected void onResume(){super.onResume();ScreenService.listener=this::refresh;if(pendingOverlay){pendingOverlay=false;if(Settings.canDrawOverlays(this))requestCapture();}if(settingsPage)engineSettings();else refresh();}
 @Override protected void onPause(){ScreenService.listener=null;super.onPause();}
 @Override protected void onSaveInstanceState(Bundle out){out.putBoolean("overlay",pendingOverlay);super.onSaveInstanceState(out);}
 private void goBack(){if(settingsPage)show();else finish();}
 @Override @android.annotation.SuppressLint("GestureBackNavigation")
  public void onBackPressed(){goBack();}
}
