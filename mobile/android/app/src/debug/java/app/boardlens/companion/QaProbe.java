package app.boardlens.companion;

import android.app.Activity;
import android.graphics.*;
import android.os.Bundle;
import java.io.*;
import org.json.*;

/** Development-only integration probe. Absent from release builds. */
public class QaProbe extends Activity {
  public void onCreate(Bundle b) {
    super.onCreate(b);
    if (getIntent().getBooleanExtra("remote", false)) {
      new Thread(
              () -> {
                JSONObject r = new JSONObject();
                try {
                  PhoneRemote remote = new PhoneRemote(this);
                  JSONObject before = remote.api("api/state", null);
                  PhoneSettings settings = new PhoneSettings(this);
                  settings
                      .p
                      .edit()
                      .putString("backend", "Computer")
                      .putString("engine", "maia3-23m")
                      .putString("evaluator", "stockfish")
                      .putFloat("seconds", .15f)
                      .putBoolean("predict", true)
                      .apply();
                  PhoneEngine.Result result =
                      remote.analyze(
                          new ChessPosition(
                              "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"),
                          settings,
                          () -> true,
                          value -> {},
                          value -> {
                            try {
                              r.put("evaluation_provider", value.getString("engine"));
                            } catch (Exception ignored) {
                            }
                          });
                  JSONObject after = remote.api("api/state", null);
                  r.put("provider", result.provider())
                      .put("move", result.lines().get(0).move())
                      .put("plies", result.lines().get(0).pv().size())
                      .put("catalog_count", before.getJSONArray("phone_engines").length())
                      .put(
                          "desktop_position_unchanged",
                          before
                              .getJSONArray("boards")
                              .getJSONObject(0)
                              .getString("fen")
                              .equals(
                                  after.getJSONArray("boards").getJSONObject(0).getString("fen")))
                      .put(
                          "desktop_engine_unchanged",
                          before.getJSONObject("settings").getInt("engine_kind")
                              == after.getJSONObject("settings").getInt("engine_kind"));
                } catch (Exception e) {
                  try {
                    r.put("error", e.toString());
                  } catch (Exception ignored) {
                  }
                }
                try (FileWriter out =
                    new FileWriter(new File(getFilesDir(), "remote-result.json"))) {
                  out.write(r.toString());
                } catch (Exception ignored) {
                }
                runOnUiThread(this::finish);
              },
              "Phone-remote-QA")
          .start();
      return;
    }
    if (getIntent().getBooleanExtra("state", false)) {
      try {
        JSONObject value =
            new JSONObject()
                .put("phone_visible", ScreenService.phoneVisible)
                .put("frames", ScreenService.frames)
                .put("reads", ScreenService.reads)
                .put("diagnostic", ScreenService.diagnostic)
                .put("running", ScreenService.running)
                .put("status", ScreenService.status)
                .put("fen", ScreenService.fen)
                .put("moves", ScreenService.suggestion)
                .put("evaluation", ScreenService.evaluation);
        try (FileWriter out = new FileWriter(new File(getFilesDir(), "live-state.json"))) {
          out.write(value.toString());
        }
      } catch (Exception ignored) {
      }
      finish();
      return;
    }
    new Thread(
            () -> {
              JSONObject report = new JSONObject();
              try (BoardReader reader = new BoardReader(this);
                  PhoneEngine engine = new PhoneEngine()) {
                JSONArray rows = new JSONArray();
                for (String name : getAssets().list("fixtures")) {
                  long start = System.currentTimeMillis();
                  Bitmap image = BitmapFactory.decodeStream(getAssets().open("fixtures/" + name));
                  BoardReader.Read read = reader.read(image, null, "Auto");
                  JSONObject r =
                      new JSONObject()
                          .put("fixture", name)
                          .put("recognized", read != null)
                          .put("elapsed_ms", System.currentTimeMillis() - start)
                          .put("diagnostic", reader.diagnostic);
                  if (read != null) {
                    r.put("placement", read.placement())
                        .put("white_bottom", read.whiteBottom())
                        .put("rect", read.rect().toShortString());
                  }
                  rows.put(r);
                  image.recycle();
                }
                report.put("recognition", rows);
                ChessPosition p =
                    new ChessPosition("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
                PhoneEngine.Result result =
                    engine.search(this, p, new PhoneSettings(this), false, null);
                report
                    .put("uci_move", result.lines().get(0).move())
                    .put("legal", p.legal().contains(result.lines().get(0).move()));
              } catch (Exception e) {
                try {
                  report.put("error", e.toString());
                } catch (Exception ignored) {
                }
              }
              try (FileWriter out = new FileWriter(new File(getFilesDir(), "qa-result.json"))) {
                out.write(report.toString());
              } catch (Exception ignored) {
              }
              runOnUiThread(this::finish);
            },
            "BoardLens-QA")
        .start();
  }
}
