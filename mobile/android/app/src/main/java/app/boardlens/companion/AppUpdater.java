package app.boardlens.companion;

import android.app.*;
import android.content.*;
import android.net.Uri;
import java.io.*;
import java.net.*;
import org.json.*;

/** Checks public releases; installation stays with Android/browser, never a custom installer. */
public final class AppUpdater {
  private final Activity activity;
  private boolean busy;
  private static final String ROOT = "https://github.com/Nick-PY0/BoardLens/releases";

  AppUpdater(Activity a) {
    activity = a;
  }

  public void check() {
    check(false);
  }

  public void check(boolean quiet) {
    android.content.SharedPreferences preferences = activity.getSharedPreferences("app-updates", 0);
    long now = System.currentTimeMillis();
    if (busy || quiet && now - preferences.getLong("lastCheck", 0) < 6 * 60 * 60 * 1000) return;
    preferences.edit().putLong("lastCheck", now).apply();
    busy = true;
    new Thread(
            () -> {
              String message;
              boolean available = false;
              try {
                HttpURLConnection c =
                    (HttpURLConnection)
                        new URL("https://api.github.com/repos/Nick-PY0/BoardLens/releases/latest")
                            .openConnection();
                c.setConnectTimeout(10000);
                c.setReadTimeout(10000);
                c.setRequestProperty("User-Agent", "BoardLens-Android");
                JSONObject release;
                try (InputStream in = c.getInputStream()) {
                  byte[] data = Streams.read(in, 2000000);
                  if (data.length > 2000000) throw new IOException("Response too large");
                  release =
                      new JSONObject(new String(data, java.nio.charset.StandardCharsets.UTF_8));
                } finally {
                  c.disconnect();
                }
                boolean apk = false;
                JSONArray assets = release.getJSONArray("assets");
                for (int i = 0; i < assets.length(); i++)
                  if (assets
                      .getJSONObject(i)
                      .getString("name")
                      .equals("BoardLens-Companion-Android.apk")) apk = true;
                long
                    current =
                        (android.os.Build.VERSION.SDK_INT >= 28
                            ? activity
                                .getPackageManager()
                                .getPackageInfo(activity.getPackageName(), 0)
                                .getLongVersionCode()
                            : activity
                                .getPackageManager()
                                .getPackageInfo(activity.getPackageName(), 0)
                                .versionCode),
                    next = 0;
                if (apk) {
                  for (int i = 0; i < assets.length(); i++) {
                    JSONObject a = assets.getJSONObject(i);
                    if (!a.getString("name").equals("boardlens-update.json")) continue;
                    String url = a.getString("browser_download_url");
                    if (!url.startsWith(ROOT + "/download/"))
                      throw new IOException("Unexpected manifest URL");
                    HttpURLConnection m = (HttpURLConnection) new URL(url).openConnection();
                    m.setConnectTimeout(10000);
                    m.setReadTimeout(10000);
                    try (InputStream in = m.getInputStream()) {
                      byte[] data = Streams.read(in, 65536);
                      if (data.length > 65536) throw new IOException("Manifest too large");
                      JSONObject manifest =
                          new JSONObject(new String(data, java.nio.charset.StandardCharsets.UTF_8));
                      next = manifest.getJSONObject("android").getLong("version_code");
                    } finally {
                      m.disconnect();
                    }
                  }
                }
                available =
                    apk
                        && next > current
                        && !release.optBoolean("prerelease")
                        && !release.optBoolean("draft");
                message =
                    available
                        ? "A BoardLens release is available. Open GitHub to download it. Android"
                            + " handles installation and keeps your settings."
                        : apk
                            ? "You have the latest version."
                            : "The Android download is currently withheld for review. Computer"
                                + " companion in your browser is still available.";
              } catch (Exception error) {
                message = "Could not check for updates. Check your connection and try again.";
              }
              String text = message;
              boolean update = available;
              activity.runOnUiThread(
                  () -> {
                    busy = false;
                    if (activity.isFinishing() || activity.isDestroyed() || quiet && !update)
                      return;
                    AlertDialog.Builder dialog =
                        new AlertDialog.Builder(activity)
                            .setTitle("BoardLens updates")
                            .setMessage(text)
                            .setNegativeButton("Close", null);
                    if (update)
                      dialog.setPositiveButton(
                          "Open release",
                          (d, w) ->
                              activity.startActivity(
                                  new Intent(Intent.ACTION_VIEW, Uri.parse(ROOT + "/latest"))));
                    dialog.show();
                  });
            },
            "BoardLens-update-check")
        .start();
  }
}
