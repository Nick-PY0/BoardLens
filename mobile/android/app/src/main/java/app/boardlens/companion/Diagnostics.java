package app.boardlens.companion;

import android.app.ActivityManager;
import android.content.*;
import android.os.Build;
import java.io.*;

/** Local scanner/crash metadata. No frames, positions, pairing keys or network upload. */
final class Diagnostics {
 private static boolean installed;
 static synchronized void install(Context context){
  if(installed)return;installed=true;Context app=context.getApplicationContext();
  Thread.UncaughtExceptionHandler previous=Thread.getDefaultUncaughtExceptionHandler();
  Thread.setDefaultUncaughtExceptionHandler((thread,error)->{
   try{record(app,error);}catch(Throwable ignored){}
   if(previous!=null)previous.uncaughtException(thread,error);
  });
 }
 static void record(Context app,Throwable error){
  StringWriter text=new StringWriter();PrintWriter writer=new PrintWriter(text);
  // Keep class/method/line evidence without exception messages, which may contain URLs.
  for(Throwable e=error;e!=null;e=e.getCause()){
   writer.println(e.getClass().getName());for(StackTraceElement frame:e.getStackTrace())writer.println("  at "+frame);
  }
  String stack=text.toString();if(stack.length()>12000)stack=stack.substring(0,12000);
  PhoneSettings settings=new PhoneSettings(app);
  app.getSharedPreferences("diagnostics",0).edit().putString("lastCrash",stack)
   .putLong("when",System.currentTimeMillis()).putString("moveEngine",settings.engine())
   .putBoolean("evaluation",settings.evaluationEnabled()).putString("downloading",ModelDownloads.current).commit();
 }
 static String report(Context context){
  var prefs=context.getSharedPreferences("diagnostics",0);StringBuilder text=new StringBuilder("BoardLens Android\n");
  try{text.append("Version: ").append(context.getPackageManager().getPackageInfo(context.getPackageName(),0).versionName).append('\n');}catch(Exception ignored){}
  PhoneSettings settings=new PhoneSettings(context);text.append("Android ").append(Build.VERSION.SDK_INT).append(" · ").append(Build.MANUFACTURER).append(' ').append(Build.MODEL)
   .append("\nMove engine: ").append(settings.engine()).append("\nEvaluation: ").append(settings.evaluationEnabled()?settings.evaluator():"Off")
   .append("\nScanning: ").append(ScreenService.running).append("\nScanner stage: ").append(ScreenService.scanStage)
   .append("\nCaptured frames: ").append(ScreenService.frames).append(" · recognition passes: ").append(ScreenService.reads)
   .append("\nCapture size: ").append(ScreenService.captureWidth).append('x').append(ScreenService.captureHeight)
   .append("\nLast frame: ").append(age(ScreenService.lastFrameAt)).append(" · last confirmed read: ").append(age(ScreenService.lastBoardAt))
   .append("\nReader detail: ").append(readerDetail(ScreenService.diagnostic))
   .append("\nDownload: ").append(ModelDownloads.current.isEmpty()?"None":ModelDownloads.current);
  if(Build.VERSION.SDK_INT>=30)try{var exits=context.getSystemService(ActivityManager.class).getHistoricalProcessExitReasons(context.getPackageName(),0,3);
   for(var exit:exits)text.append("\nProcess exit: reason ").append(exit.getReason()).append(" · status ").append(exit.getStatus()).append(" · ").append(new java.util.Date(exit.getTimestamp()));
  }catch(RuntimeException ignored){}
  String crash=prefs.getString("lastCrash","");if(!crash.isEmpty())text.append("\nLast Java crash: ").append(new java.util.Date(prefs.getLong("when",0))).append("\nEngine at crash: ").append(prefs.getString("moveEngine","")).append("\nEvaluation enabled: ").append(prefs.getBoolean("evaluation",true)).append("\nDownload at crash: ").append(prefs.getString("downloading","")).append('\n').append(crash);
  else text.append("\nNo Java crash recorded.");return text.toString();
 }
 private static String age(long at){return at==0?"None":Math.max(0,android.os.SystemClock.elapsedRealtime()-at)/1000+" s ago";}
 private static String readerDetail(String detail){int pieces=detail.indexOf(", symbols=");if(pieces>=0)detail=detail.substring(0,pieces);return detail.isEmpty()?"None":detail.substring(0,Math.min(240,detail.length()));}
 static void show(android.app.Activity activity){
  android.widget.TextView text=new android.widget.TextView(activity);text.setText(report(activity));text.setTextSize(14);text.setTextIsSelectable(true);int pad=(int)(20*activity.getResources().getDisplayMetrics().density);text.setPadding(pad,pad,pad,pad);
  android.widget.ScrollView scroll=new android.widget.ScrollView(activity);scroll.addView(text);
  new android.app.AlertDialog.Builder(activity).setTitle("Scanner diagnostics").setView(scroll).setPositiveButton("Copy",(d,w)->copy(activity)).setNegativeButton("Close",null).show();
 }
 static void copy(Context context){
  context.getSystemService(ClipboardManager.class).setPrimaryClip(ClipData.newPlainText("BoardLens diagnostics",report(context)));
  android.widget.Toast.makeText(context,"Diagnostics copied to clipboard",android.widget.Toast.LENGTH_SHORT).show();
 }
}
