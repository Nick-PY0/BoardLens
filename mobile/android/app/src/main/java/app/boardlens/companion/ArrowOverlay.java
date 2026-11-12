package app.boardlens.companion;

import android.content.Context;
import android.graphics.*;
import android.animation.ValueAnimator;
import android.view.*;
import java.util.*;

/** One passive window: never receives taps or keyboard focus. */
final class ArrowOverlay extends View {
  private final WindowManager wm;
  private boolean attached;
  private volatile Rect board;
  private volatile BoardGeometry projection;
  private volatile boolean bottom = true;
  private volatile List<String> moves = Collections.emptyList();
  private volatile float[] segments = new float[0];
  private boolean evaluationVisible;private String score="…",evaluationPosition="Auto";private float whiteShare=.5f;private volatile RectF evaluationBounds;
  private final Paint pen = new Paint(3);
  private final int[] colors = {0xffffd16c, 0xff51d9da, 0xffb0a4ff};
  private ValueAnimator evaluationAnimation;
  private float evaluationTarget=.5f;

  ArrowOverlay(Context c) {
    super(c);
    wm = (WindowManager) c.getSystemService(Context.WINDOW_SERVICE);
    setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
  }

  void show(Rect rect, boolean whiteBottom, List<String> arrows) {
    show(BoardGeometry.rectangle(rect.left,rect.top,rect.right,rect.bottom),whiteBottom,arrows);
  }

  void show(BoardGeometry geometry,boolean whiteBottom,List<String> arrows){show(geometry,whiteBottom,arrows,false,"…",.5f,"Auto");}
  void show(BoardGeometry geometry,boolean whiteBottom,List<String> arrows,boolean showEvaluation,String label,float share,String placement){
    evaluationVisible=showEvaluation;score=label;evaluationPosition=placement;
    float target=Math.max(0,Math.min(1,share));
    if(target!=evaluationTarget){
      if(evaluationAnimation!=null)evaluationAnimation.cancel();
      evaluationTarget=target;
      if(showEvaluation&&ValueAnimator.areAnimatorsEnabled()){
        evaluationAnimation=ValueAnimator.ofFloat(whiteShare,target);evaluationAnimation.setDuration(200);
        evaluationAnimation.addUpdateListener(a->{whiteShare=(float)a.getAnimatedValue();invalidate();});evaluationAnimation.start();
      }else whiteShare=target;
    }

    if(!android.provider.Settings.canDrawOverlays(getContext())){clear();remove();return;}
    projection=geometry;double[] bounds=geometry.bounds();
    board=new Rect((int)bounds[0],(int)bounds[1],(int)Math.ceil(bounds[2]),(int)Math.ceil(bounds[3]));
    bottom = whiteBottom;
    moves = new ArrayList<>(arrows);
    float[] arrowSegments = new float[arrows.size() * 4];
    for (int i = 0; i < arrows.size(); i++) {
      String m = arrows.get(i);
      PointF a = point(m.substring(0, 2)), b = point(m.substring(2, 4));
      arrowSegments[i * 4] = a.x;
      arrowSegments[i * 4 + 1] = a.y;
      arrowSegments[i * 4 + 2] = b.x;
      arrowSegments[i * 4 + 3] = b.y;
    }
    segments = arrowSegments;
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
      if(android.os.Build.VERSION.SDK_INT>=28)p.layoutInDisplayCutoutMode =
          android.os.Build.VERSION.SDK_INT >= 30
              ? WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
              : WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
      p.setTitle("BoardLens move arrows");
      try{wm.addView(this, p);attached = true;}
      catch(SecurityException|WindowManager.BadTokenException denied){
        clear();ScreenService.diagnostic="Overlay permission unavailable · enable Display over other apps";return;
      }
    }
    invalidate();
  }

  void clear() {
    segments = new float[0];evaluationVisible=false;evaluationBounds=null;
    moves = Collections.emptyList();
    invalidate();
  }

  boolean hasEvaluation(){return evaluationVisible;}
  boolean hasContent(){return hasArrows()||evaluationVisible;}

  boolean hasArrows() {
    return segments.length > 0;
  }

  void remove() {
    if(evaluationAnimation!=null)evaluationAnimation.cancel();
    if (attached) {
      try{wm.removeView(this);}catch(IllegalArgumentException ignored){}finally{attached=false;}
    }
  }

  boolean covers(int x, int y) {
    RectF panel=evaluationBounds;if(evaluationVisible&&panel!=null&&panel.contains(x,y))return true;
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
    double[] point=projection.square(square,bottom);return new PointF((float)point[0],(float)point[1]);
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
    if(evaluationVisible)drawEvaluation(canvas,location);
    canvas.restore();
  }
  private void drawEvaluation(Canvas canvas,int[] location){
    float d=getResources().getDisplayMetrics().density;WindowInsets insets=getRootWindowInsets();int top=insets==null?0:insets.getStableInsetTop(),bottomInset=insets==null?0:insets.getStableInsetBottom();
    OverlayLayout.Box box=OverlayLayout.place(projection.bounds(),getWidth()+location[0],getHeight()+location[1],d,top,bottomInset,evaluationPosition);
    RectF r=new RectF(box.left(),box.top(),box.right(),box.bottom());evaluationBounds=r;
    pen.setStyle(Paint.Style.FILL);pen.setColor(0xff12212a);canvas.drawRoundRect(r,10*d,10*d,pen);
    pen.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));pen.setTextAlign(Paint.Align.CENTER);pen.setColor(0xffc6ffe7);pen.setTextSize((box.vertical()?11:14)*d);
    String text=box.vertical()?score:"W "+score;
    if(pen.measureText(text)>r.width()-8*d)pen.setTextSize(pen.getTextSize()*(r.width()-8*d)/pen.measureText(text));
    canvas.drawText(text,r.centerX(),r.top+18*d,pen);
    RectF track=box.vertical()?new RectF(r.left+12*d,r.top+28*d,r.right-12*d,r.bottom-8*d):new RectF(r.left+10*d,r.top+28*d,r.right-10*d,r.bottom-9*d);
    pen.setColor(0xff35434d);canvas.drawRoundRect(track,4*d,4*d,pen);canvas.save();Path clip=new Path();clip.addRoundRect(track,4*d,4*d,Path.Direction.CW);canvas.clipPath(clip);pen.setColor(0xfff4f7f4);
    if(box.vertical()){float filled=track.height()*whiteShare;if(bottom)canvas.drawRect(track.left,track.bottom-filled,track.right,track.bottom,pen);else canvas.drawRect(track.left,track.top,track.right,track.top+filled,pen);}
    else canvas.drawRect(track.left,track.top,track.left+track.width()*whiteShare,track.bottom,pen);
    canvas.restore();pen.setTextAlign(Paint.Align.LEFT);
  }
}
