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
  private boolean searching;

  private synchronized void send(String s) throws IOException {
    if (input != null) {
      input.write(s);
      input.newLine();
      input.flush();
    }
  }

  private String next(long end) throws Exception {
    while (System.currentTimeMillis() < end) {
      if (cancelled) throw new CancellationException();
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

  private void start(Context c) throws Exception {
    if (process != null && process.isAlive()) return;
    if (android.os.Build.VERSION.SDK_INT < 29)
      throw new IOException("Phone engine requires Android 10 or later");
    File executable = new File(c.getApplicationInfo().nativeLibraryDir, "libstockfish.so");
    if (!executable.isFile())
      throw new IOException("No phone engine for this CPU. Use Computer companion.");
    output.clear();searching=false;
    process =
        new ProcessBuilder(executable.getAbsolutePath())
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
    send("uci");
    until("uciok", 10000);
    send("setoption name EvalFile value " + EngineFiles.network(c).getAbsolutePath());
  }

  Result search(
      Context c, ChessPosition board, PhoneSettings settings, boolean evaluation, Update update)
      throws Exception {
    return search(c,board,settings,evaluation,update,"stockfish");
  }

  Result search(Context c,ChessPosition board,PhoneSettings settings,boolean evaluation,Update update,String engineId) throws Exception {
    cancelled = false;
    start(c);
    if(searching){send("stop");until("bestmove ",5000);searching=false;}
    output.clear();
    int count = evaluation ? 1 : settings.moves();
    send("setoption name Threads value " + settings.threads());
    send("setoption name Hash value 32");
    send("setoption name MultiPV value " + count);
    send("setoption name UCI_LimitStrength value "+(engineId.equals("flounder")?"true":"false"));
    if(engineId.equals("flounder"))send("setoption name UCI_Elo value "+Math.max(1320,Math.min(3190,settings.rating())));
    send("setoption name Skill Level value " + (evaluation ? 20 : settings.skill()));
    send("isready");
    until("readyok", 5000);
    send("position fen " + board.fen());
    String mode = evaluation ? "Time + depth" : settings.mode();
    int depth = evaluation ? 18 : settings.depth();
    long ms = evaluation ? 300 : Math.max(50, Math.round(settings.seconds() * 1000));
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
      if (update != null && d >= 8 && System.currentTimeMillis() - last > 100) {
        last = System.currentTimeMillis();
        update.result(new Result(board.fen(), "Stockfish", new ArrayList<>(lines.values())));
      }
    }
    if (cancelled) throw new CancellationException();
    if (!legal.contains(best)) throw new IOException("Engine did not return a legal move");
    List<Line> ranked = new ArrayList<>(lines.values());
    String selected = best;
    ranked.sort((a, b) -> Boolean.compare(!a.move.equals(selected), !b.move.equals(selected)));
    if (ranked.stream().noneMatch(l -> l.move.equals(selected)))
      ranked.add(0, new Line(best, null, null, 0, Collections.singletonList(best)));
    return new Result(
        board.fen(),
        evaluation ? "Stockfish evaluation" : "Stockfish",
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
