package app.boardlens.companion;

import android.content.Context;
import java.io.*;
import java.net.*;
import java.security.*;
import java.util.Locale;

final class EngineFiles {
  static final String NET = "nn-1a298aa575a0.nnue",
      HASH = "1a298aa575a085434d29027978dc36867fe9c5bcea9376654b7a8eba1e52dfc2";
  static final long SIZE = 98511183;

  static File network(Context c) {
    return new File(c.getFilesDir(), NET);
  }

  static boolean ready(Context c) {
    return network(c).isFile()
        && network(c).length() == SIZE
        && c.getSharedPreferences("engine-files", 0).getString("verified", "").equals(HASH);
  }

  interface Progress {
    void update(long received, long total);
  }

  static synchronized void download(Context context, Progress progress) throws Exception {
    if (ready(context)) return;
    File partial = new File(context.getFilesDir(), NET + ".part");
    HttpURLConnection c =
        (HttpURLConnection)
            new URL(
                    "https://media.githubusercontent.com/media/official-stockfish/networks/master/"
                        + NET)
                .openConnection();
    c.setConnectTimeout(15000);
    c.setReadTimeout(30000);
    MessageDigest digest = MessageDigest.getInstance("SHA-256");
    long received = 0;
    try (InputStream in = c.getInputStream();
        FileOutputStream out = new FileOutputStream(partial)) {
      byte[] buf = new byte[65536];
      int n;
      while ((n = in.read(buf)) != -1) {
        received += n;
        if (received > SIZE) throw new IOException("Unexpected model size");
        digest.update(buf, 0, n);
        out.write(buf, 0, n);
        progress.update(received, SIZE);
      }
      StringBuilder hex = new StringBuilder();
      for (byte b : digest.digest()) hex.append(String.format(Locale.ROOT, "%02x", b & 255));
      if (received != SIZE || !hex.toString().equals(HASH))
        throw new IOException("Model checksum did not match");
      if (!partial.renameTo(network(context))) throw new IOException("Could not save model");
      context.getSharedPreferences("engine-files", 0).edit().putString("verified", HASH).apply();
    } finally {
      c.disconnect();
      partial.delete();
    }
  }
}
