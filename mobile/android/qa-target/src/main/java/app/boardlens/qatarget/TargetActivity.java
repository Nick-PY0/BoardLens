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
    android.widget.FrameLayout root = new android.widget.FrameLayout(this);
    root.addView(w, new android.widget.FrameLayout.LayoutParams(-1, -1));
    // Keep fixture controls above three-button navigation on edge-to-edge devices.
    root.setOnApplyWindowInsetsListener((view, insets) -> {
      if (android.os.Build.VERSION.SDK_INT >= 30) {
        android.graphics.Insets bars = insets.getInsets(
            android.view.WindowInsets.Type.systemBars()
                | android.view.WindowInsets.Type.displayCutout());
        view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
      } else {
        view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
            insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
      }
      return insets;
    });
    setContentView(root);
    root.requestApplyInsets();
    w.loadUrl("file:///android_asset/"+(getIntent().getBooleanExtra("fixture",false)?"fixture.html":"board.html"));
  }
}
