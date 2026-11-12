package app.boardlens.companion;

import android.content.Context;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

/** Warm, installed UCI executable. No shell and no executable downloads. */
final class PhoneEngine implements AutoCloseable {
  record Line(String move, Integer cp, Integer mate, int depth, List<String> pv) {}

  record Result(String fen, String provider, List<Line> lines) {}

  interface Update {
    void result(Result r);
  }

  private Process process;
  private BufferedWriter input;
  private final BlockingQueue<String> output = new LinkedBlockingQueue<>();
  private volatile boolean cancelled;
  private boolean searching;private volatile boolean initializing;private String processEngine="stockfish";
  private final Map<String,String> options=new HashMap<>();
  private void option(String name,String value)throws IOException{if(!value.equals(options.get(name))){send("setoption name "+name+" value "+value);options.put(name,value);}}
  void prepare(Context c,String id,PhoneSettings settings,boolean evaluation)throws Exception{
    cancelled=false;start(c,id);configure(id,settings,evaluation);
  }

  private void configure(String engineId,PhoneSettings settings,boolean evaluation)throws Exception {
    Map<String,String> before=new HashMap<>(options);
    option("Threads",String.valueOf(settings.threads()));
    if(!engineId.equals("lc0"))option("Hash","32");
    option("MultiPV",String.valueOf(evaluation?1:settings.moves()));
    if(!engineId.equals("lc0"))option("UCI_LimitStrength",engineId.equals("flounder")?"true":"false");
    if(engineId.equals("flounder"))option("UCI_Elo",String.valueOf(Math.max(1320,Math.min(3190,settings.rating()))));
    if(!engineId.equals("lc0"))option("Skill Level",String.valueOf(evaluation?20:settings.skill()));
    // Thread/hash allocation happens while warming, not after the board is read.
    // UCI position/go need no extra ready round trip when options are unchanged.
    if(!before.equals(options)){send("isready");until("readyok",5000);}
  }

  private synchronized void send(String s) throws IOException {
    if (input != null) {
      input.write(s);
      input.newLine();
      input.flush();
    }
  }

  private String next(long end) throws Exception {
    while (System.currentTimeMillis() < end) {
      if (cancelled&&!initializing) throw new CancellationException();
      String s = output.poll(60, TimeUnit.MILLISECONDS);
      if (s != null) return s;
      if (process != null && !process.isAlive())
        throw new IOException("Stockfish stopped unexpectedly");
    }
    throw new IOException("Stockfish response timed out");
  }

  private void until(String marker, int timeout) throws Exception {
    long end = System.currentTimeMillis() + timeout;
    while (!next(end).startsWith(marker)) {}
  }

  private void start(Context c,String engineId) throws Exception {
    String selected=engineId.equals("lc0")?"lc0":"stockfish";
    if(process!=null&&process.isAlive()&&!processEngine.equals(selected)){close();cancelled=false;}
    if (process != null && process.isAlive()) return;
    processEngine=selected;
    if (android.os.Build.VERSION.SDK_INT < 29)
      throw new IOException("Phone engine requires Android 10 or later");
    File executable = new File(c.getApplicationInfo().nativeLibraryDir, selected.equals("lc0")?"liblc0.so":"libstockfish.so");
    if (!executable.isFile())
      throw new IOException("No phone engine for this CPU. Use Computer companion.");
    output.clear();searching=false;options.clear();
    process =
        new ProcessBuilder(selected.equals("lc0")?java.util.Arrays.asList(executable.getAbsolutePath(),"--weights="+PhoneModels.file(c,"lc0").getAbsolutePath(),"--backend=eigen","--minibatch-size=1","--nncache=20000"):java.util.Arrays.asList(executable.getAbsolutePath()))
            .directory(c.getFilesDir())
            .redirectErrorStream(true)
            .start();
    input = new BufferedWriter(new OutputStreamWriter(process.getOutputStream()));
    Process running = process;
    Thread reader =
        new Thread(
            () -> {
              try (BufferedReader r =
                  new BufferedReader(new InputStreamReader(running.getInputStream()))) {
                String line;
                while ((line = r.readLine()) != null) output.offer(line);
              } catch (IOException ignored) {
              }
            },
            "Stockfish-output");
    reader.setDaemon(true);
    reader.start();
    initializing=true;
    try{
      send("uci");until("uciok",10000);
      if(!selected.equals("lc0"))option("EvalFile",EngineFiles.network(c).getAbsolutePath());
      send("isready");until("readyok",15000);
    }catch(Exception error){process.destroy();process=null;input=null;throw error;}
    finally{initializing=false;}

  }

  Result search(
      Context c, ChessPosition board, PhoneSettings settings, boolean evaluation, Update update)
      throws Exception {
    return search(c,board,settings,evaluation,update,"stockfish");
  }

  Result search(Context c,ChessPosition board,PhoneSettings settings,boolean evaluation,Update update,String engineId) throws Exception {
    cancelled = false;
    start(c,engineId);
    if(searching){send("stop");until("bestmove ",5000);searching=false;}
    output.clear();
    int count = evaluation ? 1 : settings.moves();
    configure(engineId,settings,evaluation);
    send("position fen " + board.fen());
    String mode = evaluation ? "Time + depth" : settings.mode();
    int depth = evaluation ? settings.evaluationDepth() : settings.depth();
    long ms = evaluation ? Math.round(settings.evaluationSeconds()*1000) : Math.max(50, Math.round(settings.seconds() * 1000));
    String limit =
        mode.equals("Depth")
            ? " depth " + depth
            : mode.equals("Time") ? " movetime " + ms : " movetime " + ms + " depth " + depth;
    searching=true;send("go" + limit);
    Map<Integer, Line> lines = new TreeMap<>();
    long end = System.currentTimeMillis() + (mode.equals("Depth") ? 120000 : ms + 15000), last = 0;
    List<String> legal = board.legal();
    String best = "";
    while (true) {
      String s = next(end);
      if (s.startsWith("bestmove ")) {
        searching=false;best = s.split(" ")[1];
        break;
      }
      if (!s.startsWith("info ")
          || !s.contains(" pv ")
          || !s.contains(" score ")
          || s.contains("bound")) continue;
      String[] fields = s.split(" +");
      int rank = 1, d = 0;
      Integer cp = null, mate = null;
      List<String> pv = new ArrayList<>();
      for (int i = 1; i < fields.length; i++) {
        if (fields[i].equals("multipv")) rank = Integer.parseInt(fields[++i]);
        else if (fields[i].equals("depth")) d = Integer.parseInt(fields[++i]);
        else if (fields[i].equals("score") && i + 2 < fields.length) {
          String type = fields[++i];
          int value = Integer.parseInt(fields[++i]) * (board.white ? 1 : -1);
          if (type.equals("cp")) cp = value;
          else if (type.equals("mate")) mate = value;
        } else if (fields[i].equals("pv")) {
          for (i++; i < fields.length; i++) pv.add(fields[i]);
          break;
        }
      }
      if (pv.isEmpty() || !legal.contains(pv.get(0))) continue;
      lines.put(rank, new Line(pv.get(0), cp, mate, d, pv));
      if (update != null && d >= 1 && (last==0||System.currentTimeMillis() - last >= 40)) {
        last = System.currentTimeMillis();
        update.result(new Result(board.fen(), engineId.equals("lc0")?"LC0":"Stockfish", new ArrayList<>(lines.values())));
      }
    }
    if (cancelled&&!initializing) throw new CancellationException();
    if (!legal.contains(best)) throw new IOException("Engine did not return a legal move");
    List<Line> ranked = new ArrayList<>(lines.values());
    String selected = best;
    ranked.sort((a, b) -> Boolean.compare(!a.move.equals(selected), !b.move.equals(selected)));
    if (ranked.stream().noneMatch(l -> l.move.equals(selected)))
      ranked.add(0, new Line(best, null, null, 0, Collections.singletonList(best)));
    return new Result(
        board.fen(),
        evaluation ? (engineId.equals("lc0")?"LC0 evaluation":"Stockfish evaluation") : (engineId.equals("lc0")?"LC0":"Stockfish"),
        ranked.subList(0, Math.min(count, ranked.size())));
  }

  void cancel() {
    cancelled = true;
    try {
      send("stop");
    } catch (IOException ignored) {
    }
  }

  public synchronized void close() {
    cancel();
    if (process != null) {
      process.destroy();
      process = null;
    }
    input = null;
  }
}
