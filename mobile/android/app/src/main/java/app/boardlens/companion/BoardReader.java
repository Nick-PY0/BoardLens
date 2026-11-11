package app.boardlens.companion;

import ai.onnxruntime.*;
import android.content.Context;
import android.graphics.*;
import java.nio.FloatBuffer;
import java.util.*;

/** Local pixels only. No images leave the phone. Supports flat, unobstructed 2D boards. */
final class BoardReader implements AutoCloseable {
  record Read(Rect rect, String placement, boolean whiteBottom, float confidence) {}

  String diagnostic = "";
  private final OrtEnvironment env = OrtEnvironment.getEnvironment();
  private final OrtSession session;

  BoardReader(Context c) throws Exception {
    try (var in = c.getAssets().open("models/chess-tiles-v2.onnx");
        var options = new OrtSession.SessionOptions()) {
      options.setIntraOpNumThreads(1);
      session = env.createSession(Streams.read(in, 2000000), options);
    }
  }

  Read read(Bitmap image, Rect previous, String orientation) throws Exception {
    if (image.getWidth() == image.getHeight()) {
      Read whole =
          classify(image, new Rect(0, 0, image.getWidth(), image.getHeight()), orientation);
      if (whole != null) return whole;
    }
    List<Rect> candidates = new ArrayList<>();
    if (previous != null
        && new Rect(0, 0, image.getWidth(), image.getHeight()).contains(previous)) {
      Read tracked = classify(image, previous, orientation);
      if (tracked != null) return tracked;
    }
    if (image.getWidth() == image.getHeight())
      candidates.add(new Rect(0, 0, image.getWidth(), image.getHeight()));
    for (Rect r : GradientBoards.detect(image)) {
      Read found = classify(image, r, orientation);
      if (found != null) return found;
    }
    for (Rect r : detect(image)) {
      boolean duplicate = false;
      for (Rect p : candidates)
        if (Math.abs(p.left - r.left) < r.width() * .1
            && Math.abs(p.top - r.top) < r.width() * .1
            && Math.abs(p.width() - r.width()) < r.width() * .1) duplicate = true;
      if (!duplicate) candidates.add(r);
    }
    for (Rect r : candidates) {
      Read result = classify(image, r, orientation);
      if (result != null) return result;
    }
    return null;
  }

  Read classify(Bitmap image, Rect r, String orientation) throws Exception {
    if (r.width() < 160 || r.height() != r.width()) return null;
    Bitmap crop = Bitmap.createBitmap(image, r.left, r.top, r.width(), r.height()),
        small = Bitmap.createScaledBitmap(crop, 256, 256, true);
    int[] pixels = new int[65536];
    small.getPixels(pixels, 0, 256, 0, 0, 256, 256);
    double gridScore = checker(pixels, 256, 256, 0, 0, 256);
    if (gridScore < .90) {
      diagnostic = "grid=" + gridScore;
      if (small != crop) small.recycle();
      if (crop != image) crop.recycle();
      return null;
    }
    float[] input = new float[64 * 1024];
    for (int row = 0; row < 8; row++)
      for (int col = 0; col < 8; col++)
        for (int y = 0; y < 32; y++)
          for (int x = 0; x < 32; x++) {
            int pixel = pixels[(row * 32 + y) * 256 + col * 32 + x];
            input[((7 - row) * 8 + col) * 1024 + y * 32 + x] =
                (Color.red(pixel) * .299f + Color.green(pixel) * .587f + Color.blue(pixel) * .114f)
                    / 255f;
          }
    if (small != crop) small.recycle();
    if (crop != image) crop.recycle();
    char[] chars = new char[64];
    float sum = 0, min = 1;
    String labels = ".KQRBNPkqrbnp";
    try (OnnxTensor tensor =
            OnnxTensor.createTensor(env, FloatBuffer.wrap(input), new long[] {64, 1024});
        OrtSession.Result output = session.run(Collections.singletonMap("tiles", tensor))) {
      float[][] probs = (float[][]) output.get(0).getValue();
      for (int i = 0; i < 64; i++) {
        int best = 0;
        for (int j = 1; j < 13; j++) if (probs[i][j] > probs[i][best]) best = j;
        float confidence = probs[i][best];
        sum += confidence;
        min = Math.min(min, confidence);
        chars[(7 - i / 8) * 8 + i % 8] = labels.charAt(best);
      }
    }
    if (min < .70f || sum / 64 < .90f) {
      diagnostic = "min=" + min + ", mean=" + sum / 64 + ", symbols=" + new String(chars);
      return null;
    }
    int wk = 0, bk = 0, wp = 0, bp = 0;
    float wy = 0, by = 0;
    for (int i = 0; i < 64; i++) {
      char c = chars[i];
      if (c == 'K') wk++;
      if (c == 'k') bk++;
      if (c == 'P') {
        wp++;
        wy += i / 8;
      }
      if (c == 'p') {
        bp++;
        by += i / 8;
      }
    }
    if (wk != 1 || bk != 1) {
      diagnostic = "king counts=" + wk + "," + bk;
      return null;
    }
    boolean bottom = true;
    if (orientation.equals("White at bottom")) bottom = true;
    else if (orientation.equals("Black at bottom")) bottom = false;
    else if (wp > 0 && bp > 0) bottom = wy / wp > by / bp;
    else {
      int w = 0, b = 0;
      for (int i = 0; i < 64; i++) {
        if (chars[i] == 'K') w = i / 8;
        if (chars[i] == 'k') b = i / 8;
      }
      bottom = w > b;
    }
    StringBuilder placement = new StringBuilder();
    for (int row = 0; row < 8; row++) {
      int empty = 0;
      for (int col = 0; col < 8; col++) {
        char c = chars[bottom ? row * 8 + col : 63 - row * 8 - col];
        if (c == '.') empty++;
        else {
          if (empty > 0) {
            placement.append(empty);
            empty = 0;
          }
          placement.append(c);
        }
      }
      if (empty > 0) placement.append(empty);
      if (row < 7) placement.append('/');
    }
    diagnostic = "";
    return new Read(new Rect(r), placement.toString(), bottom, sum / 64);
  }

  private static int distance(int a, int b) {
    int r = Color.red(a) - Color.red(b),
        g = Color.green(a) - Color.green(b),
        bl = Color.blue(a) - Color.blue(b);
    return r * r + g * g + bl * bl;
  }

  static double checker(int[] pixels, int w, int h, int x, int y, int size) {
    if (size < 160 || x < 0 || y < 0 || x + size > w || y + size > h) return 0;
    int[][] samples = new int[2][32];
    int[] count = {0, 0};
    int[] all = new int[64];
    for (int row = 0; row < 8; row++)
      for (int col = 0; col < 8; col++) {
        int[] colors = new int[4];
        int n = 0;
        for (float yy : new float[] {.13f, .87f})
          for (float xx : new float[] {.13f, .87f}) {
            int py = y + (int) ((row + yy) * size / 8),
                px = x + (int) ((col + xx) * size / 8),
                red = 0,
                green = 0,
                blue = 0;
            for (int dy = -1; dy <= 1; dy++)
              for (int dx = -1; dx <= 1; dx++) {
                int c = pixels[(py + dy) * w + px + dx];
                red += Color.red(c);
                green += Color.green(c);
                blue += Color.blue(c);
              }
            colors[n++] = Color.rgb(red / 9, green / 9, blue / 9);
          }
        ;
        int[] rr = new int[4], gg = new int[4], bb = new int[4];
        for (int i = 0; i < 4; i++) {
          rr[i] = Color.red(colors[i]);
          gg[i] = Color.green(colors[i]);
          bb[i] = Color.blue(colors[i]);
        }
        Arrays.sort(rr);
        Arrays.sort(gg);
        Arrays.sort(bb);
        int color = Color.rgb((rr[1] + rr[2]) / 2, (gg[1] + gg[2]) / 2, (bb[1] + bb[2]) / 2);
        all[row * 8 + col] = color;
        int p = (row + col) % 2;
        samples[p][count[p]++] = color;
      }
    int[] center = new int[2];
    for (int p = 0; p < 2; p++) {
      int[] rr = new int[32], gg = new int[32], bb = new int[32];
      for (int i = 0; i < 32; i++) {
        rr[i] = Color.red(samples[p][i]);
        gg[i] = Color.green(samples[p][i]);
        bb[i] = Color.blue(samples[p][i]);
      }
      Arrays.sort(rr);
      Arrays.sort(gg);
      Arrays.sort(bb);
      center[p] = Color.rgb(rr[16], gg[16], bb[16]);
    }
    if ((Color.red(center[0]) - Color.red(center[1])) * .299
            + (Color.green(center[0]) - Color.green(center[1])) * .587
            + (Color.blue(center[0]) - Color.blue(center[1])) * .114
        < -5) return 0;
    int contrast = distance(center[0], center[1]);
    if (contrast < 484) return 0;
    double limit = Math.max(400, contrast * .1024);
    int good = 0;
    for (int row = 0; row < 8; row++)
      for (int col = 0; col < 8; col++)
        if (distance(all[row * 8 + col], center[(row + col) % 2]) < limit) good++;
    return good / 64.;
  }

  static List<Rect> detect(Bitmap image) {
    float scale = Math.min(1f, 1200f / Math.max(image.getWidth(), image.getHeight()));
    Bitmap small =
        Bitmap.createScaledBitmap(
            image,
            Math.round(image.getWidth() * scale),
            Math.round(image.getHeight() * scale),
            false);
    int w = small.getWidth(), h = small.getHeight();
    int[] pix = new int[w * h];
    small.getPixels(pix, 0, w, 0, 0, w, h);
    if (small != image) small.recycle();
    Map<Integer, Integer> counts = new HashMap<>();
    for (int y = 0; y < h; y += 3)
      for (int x = 0; x < w; x += 3) {
        int c = pix[y * w + x],
            bin = (Color.red(c) / 20) * 169 + (Color.green(c) / 20) * 13 + Color.blue(c) / 20;
        counts.merge(bin, 1, Integer::sum);
      }
    List<Integer> colors = new ArrayList<>(counts.keySet());
    colors.sort((a, b) -> Integer.compare(counts.get(b), counts.get(a)));
    Map<String, int[]> votes = new HashMap<>();
    byte[] mask = new byte[w * h];
    int[] queue = new int[w * h];
    for (int index = 0; index < Math.min(16, colors.size()); index++) {
      int bin = colors.get(index),
          r = bin / 169 * 20 + 10,
          g = bin / 13 % 13 * 20 + 10,
          b = bin % 13 * 20 + 10;
      for (int i = 0; i < pix.length; i++) {
        int c = pix[i];
        mask[i] =
            (byte)
                (Math.abs(Color.red(c) - r) <= 24
                        && Math.abs(Color.green(c) - g) <= 24
                        && Math.abs(Color.blue(c) - b) <= 24
                    ? 1
                    : 0);
      }
      for (int start = 0; start < pix.length; start++) {
        if (mask[start] != 1) continue;
        int head = 0, tail = 1;
        queue[0] = start;
        mask[start] = 0;
        int minX = w, maxX = 0, minY = h, maxY = 0;
        while (head < tail) {
          int at = queue[head++], xx = at % w, yy = at / w;
          minX = Math.min(minX, xx);
          maxX = Math.max(maxX, xx);
          minY = Math.min(minY, yy);
          maxY = Math.max(maxY, yy);
          for (int side = 0; side < 4; side++) {
            int n =
                switch (side) {
                  case 0 -> xx > 0 ? at - 1 : -1;
                  case 1 -> xx < w - 1 ? at + 1 : -1;
                  case 2 -> yy > 0 ? at - w : -1;
                  default -> yy < h - 1 ? at + w : -1;
                };
            if (n >= 0 && mask[n] == 1) {
              mask[n] = 0;
              queue[tail++] = n;
            }
          }
        }
        int tw = maxX - minX + 1, th = maxY - minY + 1, cell = Math.round((tw + th) / 2f);
        if (tw < 20
            || tw > Math.min(w, h) / 5
            || tw / (float) th < .94
            || tw / (float) th > 1.06
            || tail < tw * th * .42) continue;
        for (int row = 0; row < 8; row++) {
          int yy = minY - row * cell;
          if (yy < 0 || yy + 8 * cell > h) continue;
          for (int col = 0; col < 8; col++) {
            int xx = minX - col * cell;
            if (xx < 0 || xx + 8 * cell > w) continue;
            String key =
                Math.round(xx / 4f) + ":" + Math.round(yy / 4f) + ":" + Math.round(cell / 2f);
            int[] v = votes.get(key);
            if (v == null) votes.put(key, new int[] {1, xx, yy, cell * 8});
            else v[0]++;
          }
        }
      }
    }
    List<int[]> order = new ArrayList<>(votes.values());
    order.sort((a, b) -> Integer.compare(b[0], a[0]));
    List<Rect> found = new ArrayList<>();
    for (int i = 0; i < Math.min(70, order.size()); i++) {
      int[] v = order.get(i);
      if (checker(pix, w, h, v[1], v[2], v[3]) < .86) continue;
      Rect r =
          new Rect(
              Math.round(v[1] / scale),
              Math.round(v[2] / scale),
              Math.round((v[1] + v[3]) / scale),
              Math.round((v[2] + v[3]) / scale));
      boolean duplicate = false;
      for (Rect p : found)
        if (Math.abs(p.left - r.left) < r.width() * .1 && Math.abs(p.top - r.top) < r.width() * .1)
          duplicate = true;
      if (!duplicate) found.add(r);
      if (found.size() >= 5) break;
    }
    return found;
  }

  public void close() throws OrtException {
    session.close();
  }
}
