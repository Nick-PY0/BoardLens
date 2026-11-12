package app.boardlens.companion;
import android.app.*;
import android.content.*;
import android.os.*;
import java.util.*;
import java.util.concurrent.*;

/** Explicit optional model downloads continue if the app UI is closed. */
public final class ModelDownloads extends Service {
 static volatile String current="",message="";static volatile int progress;static volatile boolean running;
 static volatile Runnable listener;
 private final java.util.concurrent.atomic.AtomicBoolean cancelled=new java.util.concurrent.atomic.AtomicBoolean();
 private final Queue<String> queue=new ConcurrentLinkedQueue<>();private final Handler main=new Handler(Looper.getMainLooper());private Thread worker;private int latestStart;private boolean destroyed;
 public android.os.IBinder onBind(Intent i){return null;}
 static void changed(){Runnable r=listener;if(r!=null)new Handler(Looper.getMainLooper()).post(r);}
 @Override public int onStartCommand(Intent intent,int flags,int startId){
  latestStart=startId;
  if(intent==null||"CANCEL".equals(intent.getAction())){cancelled.set(true);queue.clear();if(worker==null)stopSelf();return START_NOT_STICKY;}
  ArrayList<String> ids=intent.getStringArrayListExtra("models");if(ids==null||ids.isEmpty()){stopSelf();return START_NOT_STICKY;}
  for(String id:ids)if(!queue.contains(id)&&!current.equals(id))queue.add(id);
  if(worker!=null)return START_NOT_STICKY;
  getSystemService(NotificationManager.class).createNotificationChannel(new NotificationChannel("models","Engine downloads",NotificationManager.IMPORTANCE_LOW));
  cancelled.set(false);running=true;notifyProgress("Preparing engine downloads");
  worker=new Thread(()->{
   try{String id;while(!cancelled.get()&&(id=queue.poll())!=null){current=id;String label=EngineCatalog.get(id).name();message="Downloading "+label;progress=0;changed();
    EngineFiles.Progress update=(got,total)->{int next=(int)(got*100/Math.max(1,total));if(next!=progress){progress=next;message="Downloading "+label+" · "+next+"%";changed();main.post(()->notifyProgress(message));}};
    if(id.equals("stockfish"))EngineFiles.download(this,cancelled::get,update);else PhoneModels.download(this,id,cancelled::get,update);
    message=label+" is ready";changed();
   }if(cancelled.get())message="Download cancelled";else message="Selected models are ready";
   }catch(Exception error){message=cancelled.get()?"Download cancelled":"Download failed: "+error.getMessage();}
   finally{main.post(()->{worker=null;running=false;current="";changed();if(!destroyed&&!cancelled.get()&&!queue.isEmpty()){onStartCommand(new Intent(this,ModelDownloads.class).putStringArrayListExtra("models",new ArrayList<>(queue)),0,latestStart);}else stopSelf(latestStart);});}
  },"BoardLens-model-download");worker.start();return START_NOT_STICKY;
 }
 private void notifyProgress(String text){
  if(destroyed||cancelled.get())return;
  PendingIntent open=PendingIntent.getActivity(this,20,new Intent(this,ModelsActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
  PendingIntent cancel=PendingIntent.getService(this,21,new Intent(this,ModelDownloads.class).setAction("CANCEL"),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
  Notification n=new Notification.Builder(this,"models").setSmallIcon(R.drawable.icon_foreground).setContentTitle("BoardLens models").setContentText(text).setContentIntent(open).setOnlyAlertOnce(true).setOngoing(true).setProgress(100,progress,progress==0).addAction(new Notification.Action.Builder(null,"Cancel",cancel).build()).build();
  if(Build.VERSION.SDK_INT>=29)startForeground(8,n,android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);else startForeground(8,n);
 }
 @Override public void onTimeout(int startId,int type){cancelled.set(true);queue.clear();message="Download paused by Android · retry in Models";stopSelf();}
 @Override public void onDestroy(){destroyed=true;cancelled.set(true);queue.clear();running=false;main.removeCallbacksAndMessages(null);stopForeground(STOP_FOREGROUND_REMOVE);super.onDestroy();}
}
