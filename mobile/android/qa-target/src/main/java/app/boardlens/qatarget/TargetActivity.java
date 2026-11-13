package app.boardlens.qatarget;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;

public class TargetActivity extends Activity {
  public void onCreate(Bundle b) {
    super.onCreate(b);
    if(getIntent().getBooleanExtra("secure",false))getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE);
    WebView w = new WebView(this);
    w.getSettings().setJavaScriptEnabled(true);
    w.getSettings().setAllowFileAccess(true);
    setContentView(w);
    w.loadUrl("file:///android_asset/"+(getIntent().getBooleanExtra("fixture",false)?"fixture.html":"board.html"));
  }
}
