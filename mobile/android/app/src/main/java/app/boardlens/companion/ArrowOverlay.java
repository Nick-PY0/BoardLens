package app.boardlens.companion;

import android.content.Context;
import android.graphics.*;
import android.view.*;
import java.util.*;

/** One passive window: never receives taps or keyboard focus. */
final class ArrowOverlay extends View {
  private final WindowManager wm;
  private boolean attached;
  private volatile Rect board;
  private volatile boolean bottom = true;
  private volatile List<String> moves = Collections.emptyList();
  private volatile float[] segments = new float[0];
  private final Paint pen = new Paint(3);
  private final int[] colors = {0xffffd16c, 0xff51d9da, 0xffb0a4ff};

  ArrowOverlay(Context c) {
    super(c);
    wm = (WindowManager) c.getSystemService(Context.WINDOW_SERVICE);
    setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
  }

  void show(Rect rect, boolean whiteBottom, List<String> arrows) {
    board = new Rect(rect);
    bottom = whiteBottom;
    moves = new ArrayList<>(arrows);
    float[] geometry = new float[arrows.size() * 4];
    for (int i = 0; i < arrows.size(); i++) {
      String m = arrows.get(i);
      PointF a = point(m.substring(0, 2)), b = point(m.substring(2, 4));
      geometry[i * 4] = a.x;
      geometry[i * 4 + 1] = a.y;
      geometry[i * 4 + 2] = b.x;
      geometry[i * 4 + 3] = b.y;
    }
    segments = geometry;
    if (!attached) {
      WindowManager.LayoutParams p =
          new WindowManager.LayoutParams(
              -1,
              -1,
              WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
              WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                  | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                  | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
              PixelFormat.TRANSLUCENT);
      p.gravity = Gravity.TOP | Gravity.LEFT;
      p.alpha = .65f;
      p.layoutInDisplayCutoutMode =
          android.os.Build.VERSION.SDK_INT >= 30
              ? WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
              : WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
      p.setTitle("BoardLens move arrows");
      wm.addView(this, p);
      attached = true;
    }
    invalidate();
  }

  void clear() {
    segments = new float[0];
    moves = Collections.emptyList();
    invalidate();
  }

  boolean hasArrows() {
    return segments.length > 0;
  }

  void remove() {
    if (attached) {
      wm.removeView(this);
      attached = false;
    }
  }

  boolean covers(int x, int y) {
    Rect r = board;
    if (r == null) return false;
    float cell = r.width() / 8f;
    float[] g = segments;
    for (int i = 0; i < g.length; i += 4) {
      float ax = g[i],
          ay = g[i + 1],
          bx = g[i + 2],
          by = g[i + 3],
          dx = bx - ax,
          dy = by - ay,
          len = dx * dx + dy * dy,
          t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / Math.max(1, len)));
      if (Math.hypot(x - ax - t * dx, y - ay - t * dy) < cell * .08
          || Math.hypot(x - bx, y - by) < cell * .26) return true;
    }
    return false;
  }

  private PointF point(String square) {
    int x = square.charAt(0) - 'a', y = square.charAt(1) - '1';
    float c = board.width() / 8f;
    return new PointF(
        board.left + (bottom ? x + .5f : 7.5f - x) * c,
        board.top + (bottom ? 7.5f - y : y + .5f) * c);
  }

  @Override
  protected void onDraw(Canvas canvas) {
    super.onDraw(canvas);
    if (board == null) return;
    int[] location = new int[2];
    getLocationOnScreen(location);
    canvas.save();
    canvas.translate(-location[0], -location[1]);
    for (int i = 0; i < moves.size(); i++) {
      String m = moves.get(i);
      if (m.length() < 4) continue;
      PointF a = point(m.substring(0, 2)), b = point(m.substring(2, 4));
      float angle = (float) Math.atan2(b.y - a.y, b.x - a.x),
          cell = board.width() / 8f,
          head = cell * .28f;
      float bx = b.x - (float) Math.cos(angle) * head * .6f,
          by = b.y - (float) Math.sin(angle) * head * .6f;
      pen.setColor(colors[i % colors.length]);
      pen.setStrokeWidth(cell * .10f);
      pen.setStrokeCap(Paint.Cap.ROUND);
      canvas.drawLine(a.x, a.y, bx, by, pen);
      Path p = new Path();
      p.moveTo(b.x, b.y);
      p.lineTo(
          b.x - (float) Math.cos(angle - .6) * head, b.y - (float) Math.sin(angle - .6) * head);
      p.lineTo(
          b.x - (float) Math.cos(angle + .6) * head, b.y - (float) Math.sin(angle + .6) * head);
      p.close();
      pen.setStyle(Paint.Style.FILL);
      canvas.drawPath(p, pen);
    }
    canvas.restore();
  }
}
