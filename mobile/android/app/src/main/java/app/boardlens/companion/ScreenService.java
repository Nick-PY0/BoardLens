package app.boardlens.companion;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.graphics.*;
import android.hardware.display.*;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.*;
import android.os.*;
import android.util.DisplayMetrics;
import android.view.WindowManager;
import java.util.*;
import java.util.concurrent.*;

/**
 * Explicit, user-started capture. No boot receiver, accessibility service, recording or uploads.
 */
public final class ScreenService extends Service {
  static volatile long frames = 0, reads = 0;
  static volatile String diagnostic = "";
  static volatile boolean running = false, phoneVisible = false;
  static volatile String status = "Stopped",
      fen = "",
      suggestion = "Waiting for a board",
      evaluation = "—";
  static volatile Bitmap preview;
  static volatile float whiteShare = .5f;
  static volatile Runnable listener;
  private static volatile ScreenService active;

  static void setPhoneVisible(boolean visible) {
    phoneVisible = visible;
    ScreenService s = active;
    if (visible && s != null)
      s.main.post(
          () -> {
            if (s.overlay != null) s.overlay.clear();
          });
  }

  static void changed() {
    Runnable r = listener;
    if (r != null) new Handler(Looper.getMainLooper()).post(r);
  }

  private final Handler main = new Handler(Looper.getMainLooper());
  private HandlerThread captureThread;
  private Handler capture;
  private MediaProjection projection;
  private VirtualDisplay display;
  private ImageReader images;
  private BoardReader reader;
  private ArrowOverlay overlay;
  private PhoneSettings settings;
  private PhoneRemote remote;
  private Rect target;
  private ChessPosition position;
  private boolean bottom = true;
  private String pending = "", lastSettings = "";
  private int stable = 0, failures = 0;
  private long lastScan = 0;
  private volatile long generation = 0;
  private boolean cleanFrame = false;
  private int[] baseline;
  private volatile List<String> lastArrows = Collections.emptyList();
  private final PhoneEngine moves = new PhoneEngine(), evaluator = new PhoneEngine();
  private final ExecutorService moveWorker = Executors.newSingleThreadExecutor(),
      evalWorker = Executors.newSingleThreadExecutor();

  @Override
  public IBinder onBind(Intent i) {
    return null;
  }

  @Override
  public int onStartCommand(Intent intent, int flags, int id) {
    if (intent == null || "STOP".equals(intent.getAction())) {
      stopSelf();
      return START_NOT_STICKY;
    }
    if ("REFRESH".equals(intent.getAction())) {
      generation++;
      moves.cancel();
      evaluator.cancel();
      lastArrows = Collections.emptyList();
      if (overlay != null) overlay.clear();
      status = "Refreshing phone board…";
      changed();
      if (capture != null)
        capture.post(
            () -> {
              target = null;
              baseline = null;
              position = null;
              pending = "";
              stable = 0;
              lastScan = 0;
            });
      return START_NOT_STICKY;
    }
    if (running) return START_NOT_STICKY;
    try {
      active = this;
      settings = new PhoneSettings(this);
      remote = new PhoneRemote(this);
      NotificationManager nm = getSystemService(NotificationManager.class);
      nm.createNotificationChannel(
          new NotificationChannel(
              "screen", "Phone screen analysis", NotificationManager.IMPORTANCE_LOW));
      Intent stop = new Intent(this, ScreenService.class).setAction("STOP");
      PendingIntent stopAction =
          PendingIntent.getService(
              this, 2, stop, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
      PendingIntent open =
          PendingIntent.getActivity(
              this,
              1,
              new Intent(this, PhoneScreenActivity.class),
              PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
      Notification n =
          new Notification.Builder(this, "screen")
              .setSmallIcon(R.drawable.icon_foreground)
              .setContentTitle("BoardLens is reading your screen")
              .setContentText("Open BoardLens for results, or stop here.")
              .setContentIntent(open)
              .setOngoing(true)
              .addAction(new Notification.Action.Builder(null, "Stop", stopAction).build())
              .build();
      startForeground(7, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION);
      captureThread = new HandlerThread("BoardLens-pixels");
      captureThread.start();
      capture = new Handler(captureThread.getLooper());
      overlay = new ArrowOverlay(this);
      projection =
          getSystemService(MediaProjectionManager.class)
              .getMediaProjection(Activity.RESULT_OK, intent.getParcelableExtra("consent"));
      projection.registerCallback(
          new MediaProjection.Callback() {
            @Override
            public void onStop() {
              main.post(() -> stopSelf());
            }

            @Override
            public void onCapturedContentResize(int w, int h) {
              if (capture != null) capture.post(() -> resize(w, h));
            }
          },
          capture);
      DisplayMetrics metrics = new DisplayMetrics();
      getSystemService(WindowManager.class).getDefaultDisplay().getRealMetrics(metrics);
      images =
          ImageReader.newInstance(
              metrics.widthPixels, metrics.heightPixels, PixelFormat.RGBA_8888, 3);
      display =
          projection.createVirtualDisplay(
              "BoardLens phone screen",
              metrics.widthPixels,
              metrics.heightPixels,
              metrics.densityDpi,
              DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
              images.getSurface(),
              null,
              capture);
      running = true;
      status = "Reading screen · open a 2D chessboard";
      changed();
      capture.post(
          () -> {
            try {
              reader = new BoardReader(this);
              tick();
            } catch (Exception error) {
              problem(error);
            }
          });
    } catch (Exception error) {
      problem(error);
    }
    return START_NOT_STICKY;
  }

  private void resize(int w, int h) {
    if (display == null
        || images == null
        || w < 1
        || h < 1
        || images.getWidth() == w && images.getHeight() == h) return;
    ImageReader old = images;
    images = ImageReader.newInstance(w, h, PixelFormat.RGBA_8888, 3);
    display.resize(w, h, getResources().getDisplayMetrics().densityDpi);
    display.setSurface(images.getSurface());
    old.close();
    target = null;
    baseline = null;
    position = null;
    generation++;
    moves.cancel();
    evaluator.cancel();
    main.post(() -> overlay.clear());
  }

  private void problem(Exception error) {
    status = "Stopped: " + error.getMessage();
    changed();
    main.post(() -> stopSelf());
  }

  private String settingsKey() {
    return settings.p.getAll().toString();
  }

  private int[] fingerprint(Bitmap b, Rect r) {
    int[] values = new int[96 * 96];
    for (int y = 0; y < 96; y++)
      for (int x = 0; x < 96; x++) {
        int xx = r.left + (int) ((x + .5f) * r.width() / 96),
            yy = r.top + (int) ((y + .5f) * r.height() / 96);
        values[y * 96 + x] = overlay.covers(xx, yy) ? 0 : b.getPixel(xx, yy);
      }
    return values;
  }

  private boolean different(int[] a, int[] b) {
    if (a == null || b == null) return true;
    int changed = 0, total = 0;
    for (int i = 0; i < a.length; i++) {
      if (a[i] == 0 || b[i] == 0) continue;
      total++;
      int av = a[i], bv = b[i];
      if (Math.abs(Color.red(av) - Color.red(bv))
              + Math.abs(Color.green(av) - Color.green(bv))
              + Math.abs(Color.blue(av) - Color.blue(bv))
          > 30) changed++;
    }
    return changed > Math.max(6, total * .0005);
  }

  private void tick() {
    if (!running) return;
    Bitmap frame = null;
    try {
      if (phoneVisible) return;
      try (Image image = images.acquireLatestImage()) {
        if (image == null) return;
        Image.Plane plane = image.getPlanes()[0];
        int w = image.getWidth(),
            h = image.getHeight(),
            stride = plane.getRowStride() / plane.getPixelStride();
        Bitmap padded = Bitmap.createBitmap(stride, h, Bitmap.Config.ARGB_8888);
        padded.copyPixelsFromBuffer(plane.getBuffer());
        frame = Bitmap.createBitmap(padded, 0, 0, w, h);
        if (frame != padded) padded.recycle();
      }
      frames++;
      String key = settingsKey();
      if (!key.equals(lastSettings)) {
        lastSettings = key;
        generation++;
        moves.cancel();
        evaluator.cancel();
        baseline = null;
        pending = "";
        stable = 0;
      }
      if (target != null && !new Rect(0, 0, frame.getWidth(), frame.getHeight()).contains(target)) {
        target = null;
        baseline = null;
      }
      if (target != null && baseline != null && !different(baseline, fingerprint(frame, target))) {
        if (settings.arrows() && !lastArrows.isEmpty() && !overlay.hasArrows()) {
          Rect rect = new Rect(target);
          boolean orientation = bottom;
          main.post(
              () -> {
                if (running && !phoneVisible) overlay.show(rect, orientation, lastArrows);
              });
        }
        return;
      }
      // Remove our own pixels only after a real board change; never blink unchanged arrows.
      if (!cleanFrame && target != null) {
        cleanFrame = true;
        main.post(() -> overlay.clear());
        return;
      }
      cleanFrame = false;
      if (target == null && SystemClock.elapsedRealtime() - lastScan < 600) return;
      lastScan = SystemClock.elapsedRealtime();
      reads++;
      BoardReader.Read read = reader.read(frame, target, settings.orientation());
      diagnostic = reader.diagnostic;
      if (read == null) {
        if (++failures > 8) {
          target = null;
          baseline = null;
          status = "Looking for a complete 2D board";
          main.post(() -> overlay.clear());
          changed();
        }
        return;
      }
      failures = 0;
      target = read.rect();
      bottom = read.whiteBottom();
      if (!read.placement().equals(pending)) {
        pending = read.placement();
        stable = 1;
        return;
      }
      if (++stable < 2) return;
      ChessPosition synced = ChessPosition.sync(position, read.placement(), settings.turn());
      if (synced == null) {
        status = "Waiting for a legal, stable position";
        changed();
        return;
      }
      if (!settings.turn().equals("Auto") && synced.white != settings.turn().equals("White")) {
        synced.white = settings.turn().equals("White");
        if (!synced.valid()) return;
      }
      boolean changedPosition = position == null || !position.fen().equals(synced.fen());
      position = synced;
      fen = position.fen();
      baseline = fingerprint(frame, target);
      Bitmap old = preview;
      preview =
          Bitmap.createBitmap(frame, target.left, target.top, target.width(), target.height());
      if (preview == frame)
        preview =
            frame.copy(Bitmap.Config.ARGB_8888, false); // UI owns old bitmap until its next draw.
      status =
          (bottom ? "White" : "Black")
              + " at bottom · "
              + (position.white ? "White" : "Black")
              + " to move"
              + (settings.turn().equals("Auto") ? " · turn inferred" : "");
      changed();
      if (changedPosition || !key.equals(lastAnalyzedSettings)) {
        lastAnalyzedSettings = key;
        lastArrows = Collections.emptyList();
        analyze(position, new Rect(target), bottom);
      } else if (settings.arrows() && !lastArrows.isEmpty()) {
        Rect rect = new Rect(target);
        boolean orientation = bottom;
        main.post(() -> overlay.show(rect, orientation, lastArrows));
      }
    } catch (Exception error) {
      status = "Read paused: " + error.getMessage();
      changed();
    } finally {
      if (frame != null) frame.recycle();
      if (running && capture != null) capture.postDelayed(this::tick, 75);
    }
  }

  private String lastAnalyzedSettings = "";

  private void analyze(ChessPosition board, Rect rect, boolean whiteBottom) {
    long token = ++generation;
    moves.cancel();
    evaluator.cancel();
    suggestion = "Thinking…";
    evaluation = "Updating Stockfish evaluation…";
    changed();
    if (settings.backend().equals("Computer")) {
      moveWorker.submit(
          () -> {
            try {
              PhoneEngine.Result finalResult =
                  remote.analyze(
                      board,
                      settings,
                      () -> token == generation && running,
                      r -> publishMoves(r, board, rect, whiteBottom, token, false),
                      value -> {
                        try {
                          if (token != generation) return;
                          org.json.JSONObject lead = value.optJSONObject("evaluation");
                          if (lead == null) lead = value.getJSONArray("lines").getJSONObject(0);
                          evaluation = value.getString("engine") + " · " + lead.getString("score");
                          Integer cp = lead.isNull("cp") ? null : lead.getInt("cp"),
                              mate = lead.isNull("mate") ? null : lead.getInt("mate");
                          whiteShare =
                              mate != null
                                  ? (mate > 0 ? 1 : 0)
                                  : cp != null ? (float) (1 / (1 + Math.exp(-cp / 250.))) : .5f;
                          changed();
                        } catch (Exception ignored) {
                        }
                      });
              if (finalResult != null)
                publishMoves(finalResult, board, rect, whiteBottom, token, true);
            } catch (Exception error) {
              if (token == generation) {
                suggestion = "Computer: " + error.getMessage();
                changed();
              }
            }
          });
      return;
    }
    if (!EngineFiles.ready(this)) {
      suggestion = "Download the phone engine in On this phone → Engines";
      changed();
      return;
    }
    moveWorker.submit(
        () -> {
          try {
            PhoneEngine.Result result =
                moves.search(
                    this,
                    board,
                    settings,
                    false,
                    r -> publishMoves(r, board, rect, whiteBottom, token, false));
            publishMoves(result, board, rect, whiteBottom, token, true);
          } catch (CancellationException ignored) {
          } catch (Exception error) {
            if (token == generation) {
              suggestion = "Engine: " + error.getMessage();
              changed();
            }
          }
        });
    evalWorker.submit(
        () -> {
          try {
            PhoneEngine.Result result = evaluator.search(this, board, settings, true, null);
            if (token != generation || result.lines().isEmpty()) return;
            PhoneEngine.Line lead = result.lines().get(0);
            evaluation =
                "Stockfish · "
                    + (lead.mate() != null
                        ? "Mate " + lead.mate()
                        : lead.cp() != null
                            ? String.format(Locale.ROOT, "%+.2f", lead.cp() / 100.)
                            : "—");
            whiteShare =
                lead.mate() != null
                    ? (lead.mate() > 0 ? 1 : 0)
                    : lead.cp() != null ? (float) (1 / (1 + Math.exp(-lead.cp() / 250.))) : .5f;
            changed();
          } catch (CancellationException ignored) {
          } catch (Exception error) {
            if (token == generation) {
              evaluation = "Evaluation: " + error.getMessage();
              changed();
            }
          }
        });
  }

  private String displayedFen = "", displayedMove = "";

  private void publishMoves(
      PhoneEngine.Result result,
      ChessPosition board,
      Rect rect,
      boolean whiteBottom,
      long token,
      boolean finished) {
    if (token != generation || result.lines().isEmpty() || !running) return;
    PhoneEngine.Line first = result.lines().get(0);
    if (settings.steady()
        && !finished
        && displayedFen.equals(result.fen())
        && !displayedMove.equals(first.move())) return;
    displayedFen = result.fen();
    displayedMove = first.move();
    StringBuilder text = new StringBuilder();
    List<String> arrows = new ArrayList<>();
    int rank = 0;
    for (PhoneEngine.Line line : result.lines()) {
      if (settings.onlyMine() && board.white != whiteBottom) continue;
      text.append(++rank).append(". ").append(board.simple(line.move())).append('\n');
      arrows.add(line.move());
      if (rank == 1 && settings.predict() && line.pv().size() > 1) {
        ChessPosition next = board.play(line.move());
        String reply = line.pv().get(1);
        if (next.legal().contains(reply)) {
          text.append("Reply: ").append(next.simple(reply)).append('\n');
          if (!settings.onlyMine()) arrows.add(reply);
          next = next.play(reply);
          if (line.pv().size() > 2 && next.legal().contains(line.pv().get(2)))
            text.append("Then: ").append(next.simple(line.pv().get(2))).append('\n');
        }
      }
    }
    if (settings.steady() && !finished && !lastArrows.isEmpty()) {
      arrows.clear();
      arrows.addAll(lastArrows);
    }
    lastArrows = new ArrayList<>(arrows);
    suggestion = text.length() == 0 ? "Waiting for your turn" : text.toString().trim();
    changed();
    main.post(
        () -> {
          if (token == generation && running) {
            if (settings.arrows()) overlay.show(rect, whiteBottom, arrows);
            else overlay.clear();
          }
        });
  }

  @Override
  public void onDestroy() {
    active = null;
    running = false;
    generation++;
    moves.close();
    evaluator.close();
    moveWorker.shutdownNow();
    evalWorker.shutdownNow();
    main.removeCallbacksAndMessages(null);
    if (overlay != null) overlay.remove();
    if (remote != null) new Thread(remote::cancel, "Stop-phone-compute").start();
    if (capture != null) {
      capture.removeCallbacksAndMessages(null);
      capture.post(
          () -> {
            if (display != null) display.release();
            if (images != null) images.close();
            if (projection != null) projection.stop();
            if (reader != null)
              try {
                reader.close();
              } catch (Exception ignored) {
              }
            if (captureThread != null) captureThread.quitSafely();
          });
    }
    if (!status.startsWith("Stopped:")) status = "Stopped";
    changed();
    stopForeground(STOP_FOREGROUND_REMOVE);
    super.onDestroy();
  }
}
