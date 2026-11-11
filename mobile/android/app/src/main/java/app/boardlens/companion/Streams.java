package app.boardlens.companion;

import java.io.*;

final class Streams {
  static byte[] read(InputStream in, int max) throws IOException {
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    byte[] buffer = new byte[8192];
    int n, total = 0;
    while ((n = in.read(buffer)) != -1) {
      total += n;
      if (total > max) throw new IOException("Response too large");
      out.write(buffer, 0, n);
    }
    return out.toByteArray();
  }
}
