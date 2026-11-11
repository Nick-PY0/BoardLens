package app.boardlens.companion;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.*;

public class MainActivity extends Activity {
  private WebView web;
  private boolean atHome = true;
  private AppUpdater updater;
  private EditText address, code;
  private String savedAddress;
  private ValueCallback<Uri[]> chooser;
  private final int background = Color.rgb(16, 28, 23),
      foreground = Color.rgb(229, 239, 232),
      accent = Color.rgb(145, 223, 180);

  private int dp(int value) {
    return Math.round(value * getResources().getDisplayMetrics().density);
  }

  private TextView label(String value, int size) {
    TextView t = new TextView(this);
    t.setText(value);
    t.setTextSize(size);
    t.setTextColor(foreground);
    t.setPadding(0, dp(8), 0, dp(8));
    return t;
  }

  private GradientDrawable shape(int color) {
    GradientDrawable d = new GradientDrawable();
    d.setColor(color);
    d.setCornerRadius(dp(12));
    return d;
  }

  @Override
  public void onCreate(Bundle state) {
    super.onCreate(state);
    if (Build.VERSION.SDK_INT >= 33)
      getOnBackInvokedDispatcher()
          .registerOnBackInvokedCallback(
              android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::goBack);
    updater = new AppUpdater(this);
    WebView.setWebContentsDebuggingEnabled(
        (getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0);
    getWindow().setStatusBarColor(background);
    getWindow().setNavigationBarColor(background);
    savedAddress = getPreferences(0).getString("address", "");
    if (getIntent().getBooleanExtra("companion", false)) connectScreen(null);
    else home();
    if (getSharedPreferences("app-updates", 0).getBoolean("auto", true)) updater.check(true);
  }

  private void inset(View root) {
    if (Build.VERSION.SDK_INT >= 30) {
      getWindow().setDecorFitsSystemWindows(false);
      android.view.WindowManager.LayoutParams params = getWindow().getAttributes();
      params.layoutInDisplayCutoutMode =
          android.view.WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
      getWindow().setAttributes(params);
      final int left = root.getPaddingLeft(),
          top = root.getPaddingTop(),
          right = root.getPaddingRight(),
          bottom = root.getPaddingBottom();
      root.setOnApplyWindowInsetsListener(
          (v, insets) -> {
            android.graphics.Insets safe =
                insets.getInsets(
                    WindowInsets.Type.systemBars()
                        | WindowInsets.Type.displayCutout()
                        | WindowInsets.Type.ime());
            v.setPadding(
                left + safe.left, top + safe.top, right + safe.right, bottom + safe.bottom);
            return WindowInsets.CONSUMED;
          });
      root.requestApplyInsets();
    } else root.setFitsSystemWindows(true);
  }

  private void home() {
    atHome = true;
    if (web != null) {
      web.destroy();
      web = null;
    }
    ScrollView root = new ScrollView(this);
    root.setBackgroundColor(background);
    root.setFillViewport(true);
    LinearLayout col = new LinearLayout(this);
    col.setOrientation(1);
    col.setPadding(dp(24), dp(20), dp(24), dp(24));
    root.addView(col);
    ImageView logo = new ImageView(this);
    logo.setImageResource(R.drawable.boardlens_banner);
    logo.setContentDescription("BoardLens");
    logo.setScaleType(ImageView.ScaleType.CENTER_CROP);
    logo.setBackground(shape(Color.WHITE));
    logo.setClipToOutline(true);
    col.addView(logo, new LinearLayout.LayoutParams(dp(220), dp(48)));
    col.addView(label("Choose your screen", 25));
    col.addView(label("On this phone", 20));
    col.addView(
        label(
            "Scan a board in another Android app. Local engine, live moves and screen arrows.",
            15));
    Button phone = new Button(this);
    phone.setAllCaps(false);
    phone.setText("Open phone screen");
    phone.setTextColor(background);
    phone.setBackground(shape(accent));
    phone.setOnClickListener(v -> startActivity(new Intent(this, PhoneScreenActivity.class)));
    col.addView(phone, new LinearLayout.LayoutParams(-1, dp(52)));
    col.addView(label("Computer companion", 20));
    col.addView(
        label("See your computer’s boards and control its installed engines over Wi-Fi.", 15));
    Button companion = new Button(this);
    companion.setAllCaps(false);
    companion.setText("Connect to computer");
    companion.setOnClickListener(v -> connectScreen(null));
    col.addView(companion, new LinearLayout.LayoutParams(-1, dp(52)));
    Button auto = new Button(this);
    auto.setAllCaps(false);
    Runnable paint =
        () ->
            auto.setText(
                "Automatic update checks: "
                    + (getSharedPreferences("app-updates", 0).getBoolean("auto", true)
                        ? "On"
                        : "Off"));
    paint.run();
    auto.setOnClickListener(
        v -> {
          android.content.SharedPreferences p = getSharedPreferences("app-updates", 0);
          p.edit().putBoolean("auto", !p.getBoolean("auto", true)).apply();
          paint.run();
        });
    col.addView(auto, new LinearLayout.LayoutParams(-1, dp(48)));
    Button updates = new Button(this);
    updates.setAllCaps(false);
    updates.setText("Check for updates");
    updates.setOnClickListener(v -> updater.check());
    col.addView(updates, new LinearLayout.LayoutParams(-1, dp(48)));
    col.addView(label("Each section saves its own settings.", 14));
    inset(root);
    setContentView(root);
  }

  private void connectScreen(String error) {
    atHome = false;
    if (web != null) {
      web.destroy();
      web = null;
    }
    ScrollView scroll = new ScrollView(this);
    scroll.setFillViewport(true);
    scroll.setBackgroundColor(background);
    LinearLayout column = new LinearLayout(this);
    column.setOrientation(LinearLayout.VERTICAL);
    column.setPadding(dp(24), dp(24), dp(24), dp(24));
    scroll.addView(
        column,
        new ScrollView.LayoutParams(
            Math.min(getResources().getDisplayMetrics().widthPixels, dp(608)),
            -2,
            android.view.Gravity.CENTER_HORIZONTAL));
    ImageView brand = new ImageView(this);
    brand.setImageResource(R.drawable.boardlens_banner);
    brand.setContentDescription("BoardLens");
    brand.setScaleType(ImageView.ScaleType.CENTER_CROP);
    brand.setBackground(shape(Color.WHITE));
    brand.setClipToOutline(true);
    column.addView(brand, new LinearLayout.LayoutParams(dp(264), dp(58)));
    Button sections = new Button(this);
    sections.setAllCaps(false);
    sections.setText("← Sections");
    sections.setOnClickListener(v -> home());
    column.addView(sections, new LinearLayout.LayoutParams(-1, dp(44)));
    column.addView(label("Computer companion", 21));
    column.addView(label("Open BoardLens → Phone on your computer. Use the same Wi-Fi.", 16));
    if (error != null) {
      TextView message = label(error, 15);
      message.setTextColor(Color.rgb(255, 175, 163));
      column.addView(message);
    }
    column.addView(label("Computer address", 15));
    address = new EditText(this);
    address.setSingleLine();
    address.setTextColor(foreground);
    address.setHintTextColor(Color.rgb(140, 164, 149));
    address.setText(savedAddress);
    address.setHint("192.168.1.50:8789");
    address.setInputType(17);
    address.setBackground(shape(Color.rgb(31, 54, 41)));
    address.setPadding(dp(14), dp(10), dp(14), dp(10));
    column.addView(address, new LinearLayout.LayoutParams(-1, dp(52)));
    column.addView(label("Pairing code", 15));
    code = new EditText(this);
    code.setSingleLine();
    code.setTextColor(foreground);
    code.setHintTextColor(Color.rgb(140, 164, 149));
    code.setHint("Six-digit code");
    code.setInputType(2);
    code.setBackground(shape(Color.rgb(31, 54, 41)));
    code.setPadding(dp(14), dp(10), dp(14), dp(10));
    column.addView(code, new LinearLayout.LayoutParams(-1, dp(52)));
    Button connect = new Button(this);
    connect.setAllCaps(false);
    connect.setText("Connect to computer");
    connect.setTextColor(background);
    connect.setBackground(shape(accent));
    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, dp(52));
    params.topMargin = dp(24);
    column.addView(connect, params);
    connect.setOnClickListener(
        v -> {
          String raw = address.getText().toString().trim();
          if (!raw.startsWith("http://") && !raw.startsWith("https://")) raw = "http://" + raw;
          try {
            java.net.URI strict = new java.net.URI(raw);
            if (strict.getHost() == null
                || strict.getUserInfo() != null
                || !(strict.getScheme().equals("http") || strict.getScheme().equals("https"))
                || strict.getPort() > 65535
                || strict.getPort() == 0) throw new Exception();
          } catch (Exception e) {
            address.setError("Enter a valid computer address and port.");
            return;
          }
          Uri parsed = Uri.parse(raw);
          if (parsed.getHost() == null
              || parsed.getHost().isEmpty()
              || parsed.getUserInfo() != null) {
            address.setError("Enter the computer address shown in BoardLens.");
            return;
          }
          if (parsed.getPort() == -1)
            parsed = parsed.buildUpon().encodedAuthority(parsed.getHost() + ":8789").build();
          savedAddress = parsed.buildUpon().path("/").query(null).fragment(null).build().toString();
          getPreferences(0).edit().putString("address", savedAddress).apply();
          String pairing = code.getText().toString().trim();
          if (!pairing.isEmpty() && !pairing.matches("[0-9]{6}")) {
            code.setError("Use the six-digit code on your computer.");
            return;
          }
          open(savedAddress + (pairing.isEmpty() ? "" : "#pair=" + pairing));
        });
    Button updates = new Button(this);
    updates.setAllCaps(false);
    updates.setText("Check for app updates");
    updates.setOnClickListener(v -> updater.check());
    column.addView(updates, new LinearLayout.LayoutParams(-1, dp(48)));
    column.addView(
        label("Your computer keeps reading and thinking. You can minimize its window.", 14));
    inset(scroll);
    setContentView(scroll);
  }

  private void open(String url) {
    FrameLayout root = new FrameLayout(this);
    root.setBackgroundColor(background);
    web = new WebView(this);
    web.setBackgroundColor(background);
    root.addView(web, new FrameLayout.LayoutParams(-1, -1));
    web.getSettings().setJavaScriptEnabled(true);
    web.getSettings().setDomStorageEnabled(true);
    web.getSettings().setAllowFileAccess(false);
    web.getSettings().setAllowContentAccess(true);
    web.getSettings().setSupportMultipleWindows(false);
    web.addJavascriptInterface(
        new Object() {
          @android.webkit.JavascriptInterface
          public void pairedToken(String token) {
            runOnUiThread(
                () -> {
                  if (web != null
                      && web.getUrl() != null
                      && web.getUrl().startsWith(savedAddress)
                      && token.matches("[A-Za-z0-9_-]{32,128}"))
                    getSharedPreferences("computer-link", 0)
                        .edit()
                        .putString("address", savedAddress)
                        .putString("token", token)
                        .apply();
                });
          }

          @android.webkit.JavascriptInterface
          public void checkForUpdates() {
            runOnUiThread(() -> updater.check());
          }
        },
        "BoardLensDevice");
    web.setWebViewClient(
        new WebViewClient() {
          @Override
          public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri destination = request.getUrl();
            Uri base = Uri.parse(savedAddress);
            if (!base.getHost().equals(destination.getHost())
                || destination.getPort() != base.getPort()
                || !base.getScheme().equals(destination.getScheme())) {
              try {
                startActivity(new Intent(Intent.ACTION_VIEW, destination));
              } catch (android.content.ActivityNotFoundException ignored) {
              }
              return true;
            }
            return false;
          }

          @Override
          public void onReceivedError(
              WebView view, WebResourceRequest request, WebResourceError error) {
            if (request.isForMainFrame())
              runOnUiThread(
                  () ->
                      connectScreen(
                          "Could not reach the computer. Keep the desktop companion enabled, check"
                              + " the address and Wi-Fi, and allow its local connection if your"
                              + " firewall asks."));
          }
        });
    web.setWebChromeClient(
        new WebChromeClient() {
          @Override
          public boolean onShowFileChooser(
              WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
            if (chooser != null) chooser.onReceiveValue(null);
            chooser = callback;
            try {
              startActivityForResult(params.createIntent(), 100);
              return true;
            } catch (Exception e) {
              chooser = null;
              return false;
            }
          }
        });
    inset(root);
    setContentView(root);
    web.loadUrl(url);
  }

  @Override
  protected void onActivityResult(int request, int result, Intent data) {
    super.onActivityResult(request, result, data);
    if (request == 100 && chooser != null) {
      chooser.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result, data));
      chooser = null;
    }
  }

  private void goBack() {
    if (web != null) connectScreen(null);
    else if (!atHome) home();
    else finish();
  }

  @Override
  public void onBackPressed() {
    goBack();
  }

  @Override
  protected void onResume() {
    super.onResume();
    ScreenService.setPhoneVisible(true);
  }

  @Override
  protected void onPause() {
    ScreenService.setPhoneVisible(false);
    super.onPause();
  }

  @Override
  public void onDestroy() {
    if (web != null) web.destroy();
    super.onDestroy();
  }
}
