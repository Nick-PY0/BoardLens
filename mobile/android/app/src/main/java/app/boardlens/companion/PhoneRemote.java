package app.boardlens.companion;

import android.content.Context;
import android.content.SharedPreferences;
import java.io.*;
import java.net.*;
import java.util.*;
import java.util.function.*;
import org.json.*;

final class PhoneRemote {
  private final SharedPreferences link;
  private volatile String currentRequest;

  PhoneRemote(Context c) {
    link = c.getSharedPreferences("computer-link", 0);
  }

  boolean linked() {
    return !link.getString("token", "").isEmpty();
  }

  JSONObject api(String path, JSONObject data) throws Exception {
    String base = link.getString("address", "");
    URI uri = new URI(base);
    if (!linked()
        || uri.getHost() == null
        || !(uri.getScheme().equals("http") || uri.getScheme().equals("https"))
        || uri.getUserInfo() != null) throw new IOException("Pair Computer companion first");
    HttpURLConnection c = (HttpURLConnection) new URL(base + path).openConnection();
    c.setConnectTimeout(5000);
    c.setReadTimeout(6500);
    c.setInstanceFollowRedirects(false);
    c.setRequestProperty("Authorization", "Bearer " + link.getString("token", ""));
    try {
      if (data != null) {
        c.setRequestMethod("POST");
        c.setDoOutput(true);
        c.setRequestProperty("Content-Type", "application/json");
        try (OutputStream out = c.getOutputStream()) {
          out.write(data.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
        }
      }
      int code = c.getResponseCode();
      InputStream stream = code >= 400 ? c.getErrorStream() : c.getInputStream();
      if (stream == null) throw new IOException("Computer connection failed");
      JSONObject result;
      try (InputStream in = stream) {
        byte[] bytes = Streams.read(in, 4000000);
        if (bytes.length > 4000000) throw new IOException("Response too large");
        result = new JSONObject(new String(bytes, java.nio.charset.StandardCharsets.UTF_8));
      }
      if (code != 200)
        throw new IOException(result.optString("error", "Computer connection failed"));
      return result;
    } finally {
      c.disconnect();
    }
  }

  void cancel() {
    String id = currentRequest;
    if (id == null) return;
    try {
      api(
          "api/command",
          new JSONObject()
              .put("command", "cancel_phone")
              .put("data", new JSONObject().put("request_id", id)));
    } catch (Exception ignored) {
    }
  }

  static PhoneEngine.Result result(JSONObject value) throws Exception {
    List<PhoneEngine.Line> lines = new ArrayList<>();
    JSONArray items = value.getJSONArray("lines");
    for (int i = 0; i < items.length(); i++) {
      JSONObject item = items.getJSONObject(i);
      List<String> pv = new ArrayList<>();
      JSONArray moves = item.optJSONArray("pv_moves");
      if (moves != null) for (int j = 0; j < moves.length(); j++) pv.add(moves.getString(j));
      if (pv.isEmpty()) pv.add(item.getString("move"));
      lines.add(
          new PhoneEngine.Line(
              item.getString("move"),
              item.isNull("cp") ? null : item.getInt("cp"),
              item.isNull("mate") ? null : item.getInt("mate"),
              item.optInt("depth"),
              pv));
    }
    return new PhoneEngine.Result(value.getString("fen"), value.getString("engine"), lines);
  }

  PhoneEngine.Result analyze(
      ChessPosition board,
      PhoneSettings settings,
      BooleanSupplier current,
      Consumer<PhoneEngine.Result> update,
      Consumer<JSONObject> evaluation)
      throws Exception {
    String request = UUID.randomUUID().toString();
    currentRequest = request;
    JSONObject payload =
        new JSONObject()
            .put("request_id", request)
            .put("fen", board.fen())
            .put("engine", settings.engine())
            .put("evaluator", settings.evaluator())
            .put("seconds", settings.seconds())
            .put("threads", settings.threads())
            .put("skill", settings.skill())
            .put("depth", settings.depth())
            .put("moves", settings.moves())
            .put("mode", settings.mode())
            .put("rating", settings.p.getInt("rating", 1500))
            .put("predict", settings.predict())
            .put("prediction_plies", settings.predictionPlies())
            .put("prediction_seconds", settings.predictionSeconds());
    api("api/command", new JSONObject().put("command", "analyze_phone").put("data", payload));
    long until = System.currentTimeMillis() + 180000;
    String last = "", lastEval = "";
    PhoneEngine.Result latest = null;
    while (current.getAsBoolean() && System.currentTimeMillis() < until) {
      JSONObject state = api("api/phone-position", null).optJSONObject("phone_analysis");
      if (state == null || !state.optString("request_id").equals(request)) {
        Thread.sleep(150);
        continue;
      }
      if (!state.optString("error").isEmpty()) throw new IOException(state.getString("error"));
      JSONObject moves = state.optJSONObject("recommendation"),
          eval = state.optJSONObject("evaluation");
      if (moves != null && !moves.toString().equals(last)) {
        last = moves.toString();
        latest = result(moves);
        update.accept(latest);
      }
      if (eval != null && !eval.toString().equals(lastEval)) {
        lastEval = eval.toString();
        evaluation.accept(eval);
      }
      if (state.optString("status").equals("ready")) return latest;
      Thread.sleep(150);
    }
    if (current.getAsBoolean()) throw new IOException("Computer analysis timed out");
    try {
      api(
          "api/command",
          new JSONObject()
              .put("command", "cancel_phone")
              .put("data", new JSONObject().put("request_id", request)));
    } catch (Exception ignored) {
    }
    return null;
  }
}
