package app.boardlens.companion;
import java.util.concurrent.*;

/** One running search and only the newest waiting position, never a backlog. */
final class LatestWorkQueue implements AutoCloseable {
 private final ThreadPoolExecutor worker;
 private boolean closed;
 LatestWorkQueue(String name){worker=new ThreadPoolExecutor(1,1,0,TimeUnit.MILLISECONDS,new ArrayBlockingQueue<>(1),r->new Thread(r,name),new ThreadPoolExecutor.DiscardOldestPolicy());}
 synchronized void submit(Runnable task){if(closed)return;worker.getQueue().clear();worker.execute(task);}
 synchronized void close(Runnable cleanup){if(closed)return;closed=true;worker.getQueue().clear();worker.execute(cleanup);worker.shutdown();}
 public synchronized void close(){closed=true;worker.shutdownNow();}
}
