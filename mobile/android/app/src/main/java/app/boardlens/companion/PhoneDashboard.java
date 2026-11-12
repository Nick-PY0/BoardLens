package app.boardlens.companion;

import android.content.Context;
import android.graphics.Bitmap;
import android.view.Gravity;
import android.view.View;
import android.widget.*;

/** Dashboard view shared with the isolated visual preview. */
final class PhoneDashboard {
  interface Actions {
    void start();void stop();void hide();void scan();void settings();void help();void back();
    boolean option(String key,boolean fallback);void option(String key,boolean value,boolean unused);
  }
  final ScrollView root;final TextView status,moves,eval,engine;final ImageView preview;
  final ProgressBar bar;private final Button start,hide,stop;private final MobileUi ui;
  PhoneDashboard(Context c,Actions a){
    ui=new MobileUi(c);root=new ScrollView(c);root.setBackgroundColor(MobileUi.BG);root.setFillViewport(true);
    LinearLayout col=ui.column();col.setPadding(ui.dp(20),ui.dp(14),ui.dp(20),ui.dp(24));root.addView(col);
    LinearLayout header=new LinearLayout(c);header.setGravity(Gravity.CENTER_VERTICAL);
    Button back=ui.button("‹",false,a::back);back.setTextSize(26);back.setContentDescription("Back to sections");header.addView(back,new LinearLayout.LayoutParams(ui.dp(48),ui.dp(48)));
    TextView title=ui.text("Phone screen",22,MobileUi.FG,true);LinearLayout.LayoutParams tp=new LinearLayout.LayoutParams(0,-2,1);tp.leftMargin=ui.dp(12);header.addView(title,tp);
    Button settings=ui.button("Settings",false,a::settings);header.addView(settings,new LinearLayout.LayoutParams(-2,ui.dp(48)));col.addView(header);ui.gap(col,20);
    LinearLayout state=ui.card();TextView live=ui.text("LIVE ANALYSIS",11,MobileUi.ACCENT,true);live.setLetterSpacing(.12f);state.addView(live);ui.gap(state,10);engine=ui.text("",13,MobileUi.MUTED,false);state.addView(engine);ui.gap(state,10);
    status=ui.text("Ready to start",14,MobileUi.MUTED,false);state.addView(status);ui.gap(state,16);
    moves=ui.text("Open a chessboard",23,MobileUi.FG,true);state.addView(moves);ui.gap(state,10);
    eval=ui.text("Evaluation appears after a clean read",13,MobileUi.MUTED,false);state.addView(eval);ui.gap(state,12);
    bar=new ProgressBar(c,null,android.R.attr.progressBarStyleHorizontal);bar.setMax(1000);bar.setProgress(500);bar.setProgressTintList(android.content.res.ColorStateList.valueOf(MobileUi.ACCENT));bar.setProgressBackgroundTintList(android.content.res.ColorStateList.valueOf(MobileUi.BORDER));bar.setContentDescription("Evaluation from White's perspective");state.addView(bar,new LinearLayout.LayoutParams(-1,ui.dp(8)));
    preview=new ImageView(c);preview.setScaleType(ImageView.ScaleType.FIT_CENTER);preview.setContentDescription("Last recognized board");preview.setVisibility(View.GONE);LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(-1,ui.dp(280));bp.topMargin=ui.dp(16);state.addView(preview,bp);col.addView(state);ui.gap(col,16);
    start=ui.button("Start screen analysis",true,a::start);col.addView(start,new LinearLayout.LayoutParams(-1,ui.dp(52)));ui.gap(col,8);
    LinearLayout row=new LinearLayout(c);hide=ui.button("Open another app",false,a::hide);stop=ui.button("Stop",false,a::stop);row.addView(hide,new LinearLayout.LayoutParams(0,ui.dp(48),1));LinearLayout.LayoutParams sp=new LinearLayout.LayoutParams(ui.dp(84),ui.dp(48));sp.leftMargin=ui.dp(8);row.addView(stop,sp);col.addView(row);ui.gap(col,20);
    LinearLayout options=ui.card();options.addView(ui.toggle("Screen arrows","Tap and drag through the arrows",a.option("arrows",true),v->a.option("arrows",v,true)));options.addView(ui.toggle("Only my color","Use the side at the bottom",a.option("onlyMine",false),v->a.option("onlyMine",v,true)));col.addView(options);ui.gap(col,14);
    LinearLayout foot=new LinearLayout(c);Button scan=ui.button("Scan now",false,a::scan),help=ui.button("Help",false,a::help);foot.addView(scan,new LinearLayout.LayoutParams(0,ui.dp(48),1));LinearLayout.LayoutParams hp=new LinearLayout.LayoutParams(0,ui.dp(48),1);hp.leftMargin=ui.dp(8);foot.addView(help,hp);col.addView(foot);ui.gap(col,14);
    col.addView(ui.text("After Start, leave this screen to read boards in other apps.",13,MobileUi.MUTED,false));
  }
  void render(boolean running,String state,String recommendation,String evaluation,float whiteShare,Bitmap board){
    status.setText(state);moves.setText(recommendation);eval.setText(evaluation);bar.setProgress(Math.round(whiteShare*1000));start.setText(running?"Analysis is running":"Start screen analysis");start.setEnabled(!running);start.setAlpha(running?.55f:1f);stop.setEnabled(running);hide.setEnabled(running);hide.setAlpha(running?1f:.45f);
    preview.setVisibility(board==null?View.GONE:View.VISIBLE);if(board!=null)preview.setImageBitmap(board);
  }
}
