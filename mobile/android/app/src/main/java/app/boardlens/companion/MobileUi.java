package app.boardlens.companion;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.*;

/** Small shared native components. No permissions, network or background work. */
final class MobileUi {
  static final int BG=0xff0e151b, SURFACE=0xff182229, BORDER=0xff2b3942,
      FG=0xffedf4f4, MUTED=0xffa1b2bc, ACCENT=0xffa1e6cc, INK=0xff12251f;
  static void inset(android.app.Activity activity,View root){
    if(android.os.Build.VERSION.SDK_INT>=30){
      activity.getWindow().setDecorFitsSystemWindows(false);
      root.setOnApplyWindowInsetsListener((v,insets)->{android.graphics.Insets safe=insets.getInsets(android.view.WindowInsets.Type.systemBars()|android.view.WindowInsets.Type.displayCutout()|android.view.WindowInsets.Type.ime());v.setPadding(safe.left,safe.top,safe.right,safe.bottom);return android.view.WindowInsets.CONSUMED;});root.requestApplyInsets();
    }else root.setFitsSystemWindows(true);
  }
  final Context c;
  MobileUi(Context context){c=context;}
  int dp(int n){return Math.round(n*c.getResources().getDisplayMetrics().density);}
  GradientDrawable shape(int color,int radius){
    GradientDrawable d=new GradientDrawable(); d.setColor(color);d.setCornerRadius(dp(radius));
    if(color==SURFACE)d.setStroke(dp(1),BORDER);return d;
  }
  TextView text(String value,int size,int color,boolean bold){
    TextView t=new TextView(c);t.setText(value);t.setTextColor(color);t.setTextSize(size);
    t.setFontFeatureSettings("tnum");t.setIncludeFontPadding(false);
    if(bold)t.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));return t;
  }
  LinearLayout column(){LinearLayout v=new LinearLayout(c);v.setOrientation(LinearLayout.VERTICAL);return v;}
  LinearLayout card(){LinearLayout v=column();v.setPadding(dp(16),dp(16),dp(16),dp(16));v.setBackground(shape(SURFACE,20));return v;}
  void gap(LinearLayout v,int height){v.addView(new View(c),new LinearLayout.LayoutParams(1,dp(height)));}
  Button button(String label,boolean primary,Runnable action){
    Button b=new Button(c);b.setAllCaps(false);b.setText(label);b.setTextSize(15);b.setTextColor(primary?INK:FG);
    b.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));b.setMinHeight(dp(48));b.setMinimumHeight(dp(48));
    b.setPadding(dp(14),0,dp(14),0);b.setStateListAnimator(null);b.setBackground(shape(primary?ACCENT:SURFACE,14));
    b.setOnClickListener(v->action.run());return b;
  }
  LinearLayout toggle(String title,String description,boolean on,java.util.function.Consumer<Boolean> change){
    LinearLayout row=new LinearLayout(c);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(0,dp(8),0,dp(8));
    LinearLayout labels=column();labels.addView(text(title,15,FG,true));
    if(!description.isEmpty()){gap(labels,4);labels.addView(text(description,12,MUTED,false));}
    row.addView(labels,new LinearLayout.LayoutParams(0,-2,1));
    Button state=button(on?"On":"Off",on,()->{});final boolean[] checked={on};
    state.setContentDescription(title+": "+(on?"On":"Off"));state.setSelected(on);
    state.setOnClickListener(v->{checked[0]=!checked[0];state.setText(checked[0]?"On":"Off");state.setTextColor(checked[0]?INK:FG);state.setBackground(shape(checked[0]?ACCENT:BORDER,24));state.setSelected(checked[0]);state.setContentDescription(title+": "+(checked[0]?"On":"Off"));change.accept(checked[0]);});
    state.setBackground(shape(on?ACCENT:BORDER,24));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(dp(64),dp(48));p.leftMargin=dp(12);row.addView(state,p);return row;
  }
  View choice(String title,String[] items,int selected,java.util.function.IntConsumer change){
    LinearLayout col=column();col.addView(text(title,14,MUTED,false));gap(col,6);
    LinearLayout row=new LinearLayout(c);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(14),0,dp(12),0);row.setBackground(shape(SURFACE,14));
    final int[] at={Math.max(0,selected)};TextView value=text(items[at[0]],15,FG,true);value.setSingleLine();value.setEllipsize(android.text.TextUtils.TruncateAt.END);row.addView(value,new LinearLayout.LayoutParams(0,dp(48),1));value.setGravity(Gravity.CENTER_VERTICAL);
    View arrow=new View(c){final android.graphics.Paint pen=new android.graphics.Paint(3);protected void onDraw(android.graphics.Canvas canvas){pen.setColor(FG);pen.setStrokeWidth(dp(2));pen.setStrokeCap(android.graphics.Paint.Cap.ROUND);pen.setStyle(android.graphics.Paint.Style.STROKE);android.graphics.Path path=new android.graphics.Path();path.moveTo(dp(4),dp(8));path.lineTo(dp(10),dp(14));path.lineTo(dp(16),dp(8));canvas.drawPath(path,pen);}};row.addView(arrow,new LinearLayout.LayoutParams(dp(20),dp(22)));row.setFocusable(true);row.setContentDescription(title+": "+items[at[0]]);
    row.setOnClickListener(v->new android.app.AlertDialog.Builder(c).setTitle(title).setSingleChoiceItems(items,at[0],(dialog,index)->{at[0]=index;value.setText(items[index]);row.setContentDescription(title+": "+items[index]);change.accept(index);dialog.dismiss();}).setNegativeButton("Cancel",null).show());col.addView(row);return col;
  }
  static final class Stepper extends LinearLayout {
    private int value;private final int min,max;private final TextView label;private final java.util.function.IntConsumer changed;
    Stepper(MobileUi ui,int low,int high,int current,java.util.function.IntConsumer listener){this(ui,low,high,current,1,listener);}
    Stepper(MobileUi ui,int low,int high,int current,int step,java.util.function.IntConsumer listener){
      super(ui.c);min=low;max=high;value=Math.max(low,Math.min(high,current));changed=listener;setGravity(Gravity.CENTER_VERTICAL);
      Button minus=ui.button("−",false,()->setValue(value-step));minus.setContentDescription("Decrease");
      label=ui.text(String.valueOf(value),17,FG,true);label.setGravity(Gravity.CENTER);label.setContentDescription("Current value: "+value);
      Button plus=ui.button("+",false,()->setValue(value+step));plus.setContentDescription("Increase");
      addView(minus,new LayoutParams(ui.dp(48),ui.dp(48)));addView(label,new LayoutParams(0,ui.dp(48),1));addView(plus,new LayoutParams(ui.dp(48),ui.dp(48)));
    }
    void setValue(int next){int n=Math.max(min,Math.min(max,next));if(n==value)return;value=n;label.setText(String.valueOf(value));label.setContentDescription("Current value: "+value);changed.accept(value);}
    int getValue(){return value;}
    @Override public void setEnabled(boolean enabled){super.setEnabled(enabled);for(int i=0;i<getChildCount();i++)getChildAt(i).setEnabled(enabled);}
  }
}
