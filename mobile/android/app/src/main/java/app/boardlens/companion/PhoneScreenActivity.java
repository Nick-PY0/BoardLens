package app.boardlens.companion;

import android.app.*;
import android.content.*;
import android.graphics.drawable.GradientDrawable;
import android.media.projection.*;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.widget.*;

/** Standalone section, intentionally independent of the computer's WebView/settings. */
public class PhoneScreenActivity extends Activity {
  private PhoneSettings settings;
  private final java.util.Map<String, View> engineControls = new java.util.HashMap<>();
  private TextView status, moves, eval;
  private ImageView preview;
  private ProgressBar bar;
  private LinearLayout content;
  private final int bg = 0xff101e19, fg = 0xffe7f0e9, accent = 0xff91dfb4;
  private boolean building, settingsPage;

  int dp(int n) {
    return Math.round(n * getResources().getDisplayMetrics().density);
  }

  TextView text(String s, int size) {
    TextView t = new TextView(this);
    t.setText(s);
    t.setTextColor(fg);
    t.setTextSize(size);
    t.setPadding(0, dp(6), 0, dp(6));
    return t;
  }

  GradientDrawable shape(int color) {
    GradientDrawable d = new GradientDrawable();
    d.setColor(color);
    d.setCornerRadius(dp(12));
    return d;
  }

  Button button(String title, Runnable action) {
    Button b = new Button(this);
    b.setText(title);
    b.setAllCaps(false);
    b.setTextColor(fg);
    b.setBackground(shape(0xff2c4c3b));
    b.setOnClickListener(v -> action.run());
    LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, dp(48));
    p.topMargin = dp(8);
    content.addView(b, p);
    return b;
  }

  @Override
  public void onCreate(Bundle state) {
    super.onCreate(state);
    if (Build.VERSION.SDK_INT >= 33)
      getOnBackInvokedDispatcher()
          .registerOnBackInvokedCallback(
              android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::goBack);
    settings = new PhoneSettings(this);
    getWindow().setStatusBarColor(bg);
    getWindow().setNavigationBarColor(bg);
    show();
  }

  private void show() {
    settingsPage = false;
    building = true;
    ScrollView scroll = new ScrollView(this);
    scroll.setFillViewport(true);
    scroll.setBackgroundColor(bg);
    content = new LinearLayout(this);
    content.setOrientation(1);
    content.setPadding(dp(20), dp(12), dp(20), dp(24));
    scroll.addView(content);
    content.addView(text("On this phone", 24));
    content.addView(text("Read a board in another app.", 14));
    LinearLayout actions = new LinearLayout(this);
    Button start = new Button(this);
    start.setAllCaps(false);
    start.setText("Start");
    start.setTextColor(bg);
    start.setBackground(shape(accent));
    start.setOnClickListener(v -> start());
    Button stop = new Button(this);
    stop.setAllCaps(false);
    stop.setText("Stop");
    stop.setOnClickListener(v -> stopService(new Intent(this, ScreenService.class)));
    actions.addView(start, new LinearLayout.LayoutParams(0, dp(48), 1));
    actions.addView(stop, new LinearLayout.LayoutParams(0, dp(48), 1));
    content.addView(actions);
    status = text("", 14);
    content.addView(status);
    moves = text("", 20);
    content.addView(moves);
    eval = text("", 15);
    content.addView(eval);
    bar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
    bar.setMax(1000);
    android.graphics.drawable.LayerDrawable balance =
        new android.graphics.drawable.LayerDrawable(
            new android.graphics.drawable.Drawable[] {
              shape(0xff101713),
              new android.graphics.drawable.ClipDrawable(
                  shape(fg), Gravity.LEFT, android.graphics.drawable.ClipDrawable.HORIZONTAL)
            });
    balance.setId(0, android.R.id.background);
    balance.setId(1, android.R.id.progress);
    bar.setProgressDrawable(balance);
    bar.setContentDescription("Evaluation from White's perspective");
    content.addView(bar, new LinearLayout.LayoutParams(-1, dp(12)));
    preview = new ImageView(this);
    preview.setScaleType(ImageView.ScaleType.FIT_CENTER);
    preview.setContentDescription("Last recognized board");
    content.addView(preview, new LinearLayout.LayoutParams(-1, dp(240)));
    button(
        "Scan now",
        () -> {
          if (ScreenService.running)
            startService(new Intent(this, ScreenService.class).setAction("REFRESH"));
          else start();
        });
    toggle("Screen arrows", "arrows", true);
    toggle("Only my color", "onlyMine", false);
    toggle("Predict reply and my next move", "predict", true);
    toggle("Steady arrows", "steady", true);
    button("Engines & settings", this::engineSettings);
    button(
        "Help",
        () ->
            new AlertDialog.Builder(this)
                .setTitle("Phone screen analysis")
                .setMessage(
                    "1. Download the phone engine in Engines & settings.\n"
                        + "2. Press Start, allow screen capture, and open a 2D board in another"
                        + " app.\n"
                        + "3. Allow Display over other apps to see arrows. Arrows pass taps"
                        + " through.\n\n"
                        + "Recognition runs on this phone. On phone mode analyzes locally; Computer"
                        + " mode sends only the recognized position to your paired computer. No"
                        + " screenshots are saved or sent. Stop from this screen or the"
                        + " notification. Android asks for screen permission each session.\n\n"
                        + "Keep the complete board visible. 3D boards and unsupported piece styles"
                        + " may not read. Auto turn follows legal changes; on a midgame first scan"
                        + " choose White or Black in settings. Computer companion is a separate"
                        + " section with the desktop's engines and settings.")
                .setPositiveButton("Got it", null)
                .show());
    button("← Sections", this::finish);
    inset(scroll);
    setContentView(scroll);
    building = false;
    refresh();
  }

  private void inset(View root) {
    if (Build.VERSION.SDK_INT >= 30) {
      getWindow().setDecorFitsSystemWindows(false);
      root.setOnApplyWindowInsetsListener(
          (v, insets) -> {
            android.graphics.Insets safe =
                insets.getInsets(
                    WindowInsets.Type.systemBars()
                        | WindowInsets.Type.displayCutout()
                        | WindowInsets.Type.ime());
            v.setPadding(safe.left, safe.top, safe.right, safe.bottom);
            return WindowInsets.CONSUMED;
          });
      root.requestApplyInsets();
    } else root.setFitsSystemWindows(true);
  }

  private void toggle(String title, String key, boolean fallback) {
    Button b = button("", () -> {});
    Runnable paint =
        () -> {
          boolean on = settings.p.getBoolean(key, fallback);
          b.setText(title + "   " + (on ? "On" : "Off"));
          b.setTextColor(on ? bg : fg);
          b.setBackground(shape(on ? accent : 0xff2c4c3b));
        };
    b.setOnClickListener(
        v -> {
          settings.p.edit().putBoolean(key, !settings.p.getBoolean(key, fallback)).apply();
          paint.run();
        });
    paint.run();
  }

  private void select(String title, String key, String[] values, String current) {
    content.addView(text(title, 14));
    Spinner s = new Spinner(this);
    ArrayAdapter<String> a =
        new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, values);
    s.setAdapter(a);
    engineControls.put(key, s);
    for (int i = 0; i < values.length; i++) if (values[i].equals(current)) s.setSelection(i);
    content.addView(s, new LinearLayout.LayoutParams(-1, dp(48)));
    s.setOnItemSelectedListener(
        new AdapterView.OnItemSelectedListener() {
          public void onNothingSelected(AdapterView<?> p) {}

          public void onItemSelected(AdapterView<?> p, View v, int at, long id) {
            settings.p.edit().putString(key, values[at]).apply();
            refreshLimits();
          }
        });
  }

  private void number(String title, String key, int min, int max, int current) {
    content.addView(text(title, 14));
    NumberPicker n = new NumberPicker(this);
    engineControls.put(key, n);
    n.setMinValue(min);
    n.setMaxValue(max);
    n.setValue(current);
    n.setWrapSelectorWheel(false);
    n.setOnValueChangedListener((v, old, value) -> settings.p.edit().putInt(key, value).apply());
    content.addView(n, new LinearLayout.LayoutParams(-1, dp(120)));
  }

  private void engineSettings() {
    settingsPage = true;
    engineControls.clear();
    ScrollView scroll = new ScrollView(this);
    scroll.setBackgroundColor(bg);
    content = new LinearLayout(this);
    content.setPadding(dp(20), dp(12), dp(20), dp(24));
    content.setOrientation(1);
    scroll.addView(content);
    content.addView(text("Phone engines", 24));
    content.addView(
        text(
            "Stockfish runs here. Computer companion offers your installed Maia models, Tiny bots"
                + " and custom engines.",
            14));
    button(
        EngineFiles.ready(this) ? "Stockfish model installed" : "Download Stockfish model · 99 MB",
        () -> {
          if (EngineFiles.ready(this)) {
            Toast.makeText(this, "Stockfish is ready", Toast.LENGTH_SHORT).show();
            return;
          }
          ProgressDialog progress = new ProgressDialog(this);
          progress.setProgressStyle(ProgressDialog.STYLE_HORIZONTAL);
          progress.setMax(100);
          progress.setTitle("Stockfish evaluation data");
          progress.setMessage("Verified download from official-stockfish/networks");
          progress.setCancelable(false);
          progress.show();
          new Thread(
                  () -> {
                    try {
                      EngineFiles.download(
                          this,
                          (got, total) ->
                              runOnUiThread(() -> progress.setProgress((int) (got * 100 / total))));
                      runOnUiThread(
                          () -> {
                            progress.dismiss();
                            Toast.makeText(this, "Stockfish is ready", Toast.LENGTH_LONG).show();
                          });
                    } catch (Exception e) {
                      runOnUiThread(
                          () -> {
                            progress.dismiss();
                            new AlertDialog.Builder(this)
                                .setMessage("Download failed: " + e.getMessage())
                                .setPositiveButton("OK", null)
                                .show();
                          });
                    }
                  },
                  "Stockfish-model")
              .start();
        });
    select("Run engines", "backend", new String[] {"On phone", "Computer"}, settings.backend());
    PhoneRemote remote = new PhoneRemote(this);
    if (remote.linked()) {
      TextView connection = text("Loading computer engines…", 14);
      content.addView(connection);
      LinearLayout engineOptions = new LinearLayout(this);
      engineOptions.setOrientation(1);
      content.addView(engineOptions);
      new Thread(
              () -> {
                try {
                  org.json.JSONArray catalog =
                      remote.api("api/state", null).getJSONArray("phone_engines");
                  runOnUiThread(
                      () -> {
                        connection.setText("Computer engines (for phone-screen positions)");
                        try {
                          engineSelect(engineOptions, "Recommend moves", "engine", catalog, false);
                          engineSelect(
                              engineOptions, "Evaluation engine", "evaluator", catalog, true);
                        } catch (Exception e) {
                          connection.setText(e.getMessage());
                        }
                      });
                } catch (Exception e) {
                  runOnUiThread(
                      () -> connection.setText("Computer unavailable · keep it running on Wi-Fi"));
                }
              },
              "Phone-engine-catalog")
          .start();
    } else
      button(
          "Pair computer for Maia and Tiny bots",
          () -> startActivity(new Intent(this, MainActivity.class).putExtra("companion", true)));
    number("Maia / Flounder target rating", "rating", 600, 2600, settings.p.getInt("rating", 1500));
    select("Search limit", "mode", new String[] {"Time", "Depth", "Time + depth"}, settings.mode());
    content.addView(text("Think time (seconds)", 14));
    EditText seconds = new EditText(this);
    engineControls.put("seconds", seconds);
    seconds.setTextColor(fg);
    seconds.setInputType(8194);
    seconds.setSingleLine();
    seconds.setText(String.valueOf(settings.seconds()));
    content.addView(seconds);
    seconds.addTextChangedListener(
        new android.text.TextWatcher() {
          public void beforeTextChanged(CharSequence s, int a, int c, int f) {}

          public void onTextChanged(CharSequence s, int a, int before, int count) {
            try {
              float value = Float.parseFloat(s.toString());
              if (Float.isFinite(value) && value >= .05 && value <= 30)
                settings.p.edit().putFloat("seconds", value).apply();
              else seconds.setError("0.05 to 30 seconds");
            } catch (Exception ignored) {
              seconds.setError("Enter seconds");
            }
          }

          public void afterTextChanged(android.text.Editable s) {}
        });
    number("Depth cap", "depth", 1, 30, settings.depth());
    number("Recommended moves", "moves", 1, 5, settings.moves());
    number(
        "CPU threads",
        "threads",
        1,
        Math.max(1, Math.min(8, Runtime.getRuntime().availableProcessors())),
        settings.threads());
    number("Stockfish skill", "skill", 0, 20, settings.skill());
    select(
        "Board orientation",
        "orientation",
        new String[] {"Auto", "White at bottom", "Black at bottom"},
        settings.orientation());
    select(
        "Side to move on first scan",
        "turn",
        new String[] {"Auto", "White", "Black"},
        settings.turn());
    content.addView(text("Evaluation runs separately from recommendations.", 14));
    content.addView(text("Settings save automatically.", 14));
    button("← Phone screen", this::show);
    inset(scroll);
    setContentView(scroll);
  }

  private void start() {
    if (Build.VERSION.SDK_INT >= 33
        && checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
            != android.content.pm.PackageManager.PERMISSION_GRANTED
        && !settings.p.getBoolean("notificationAsked", false)) {
      settings.p.edit().putBoolean("notificationAsked", true).apply();
      requestPermissions(new String[] {android.Manifest.permission.POST_NOTIFICATIONS}, 9);
      return;
    }
    if (Build.VERSION.SDK_INT < 29) {
      new AlertDialog.Builder(this)
          .setMessage(
              "On-phone engines need Android 10 or later. Computer companion still works on this"
                  + " device.")
          .setPositiveButton("OK", null)
          .show();
      return;
    }
    if (settings.backend().equals("On phone") && !EngineFiles.ready(this)) {
      engineSettings();
      return;
    }
    if (!Settings.canDrawOverlays(this) && settings.arrows()) {
      new AlertDialog.Builder(this)
          .setTitle("Allow move arrows")
          .setMessage(
              "Enable Display over other apps for BoardLens, then return and press Start. This"
                  + " draws passive arrows over a chessboard.")
          .setNegativeButton(
              "No arrows",
              (d, w) -> {
                settings.p.edit().putBoolean("arrows", false).apply();
                requestCapture();
              })
          .setPositiveButton(
              "Open settings",
              (d, w) ->
                  startActivity(
                      new Intent(
                          Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                          Uri.parse("package:" + getPackageName()))))
          .show();
      return;
    }
    requestCapture();
  }

  private void requestCapture() {
    if (ScreenService.running) {
      moveTaskToBack(true);
      return;
    }
    MediaProjectionManager m = getSystemService(MediaProjectionManager.class);
    Intent i =
        Build.VERSION.SDK_INT >= 34
            ? m.createScreenCaptureIntent(MediaProjectionConfig.createConfigForDefaultDisplay())
            : m.createScreenCaptureIntent();
    startActivityForResult(i, 42);
  }

  @Override
  public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
    super.onRequestPermissionsResult(request, permissions, results);
    if (request == 9) start();
  }

  @Override
  protected void onActivityResult(int request, int result, Intent data) {
    super.onActivityResult(request, result, data);
    if (request == 42 && result == RESULT_OK && data != null) {
      startForegroundService(new Intent(this, ScreenService.class).putExtra("consent", data));
      moveTaskToBack(true);
    }
  }

  private void refresh() {
    if (isFinishing()) return;
    status.setText(ScreenService.status);
    moves.setText(ScreenService.suggestion);
    eval.setText(ScreenService.evaluation);
    bar.setProgress((int) (ScreenService.whiteShare * 1000));
    if (ScreenService.preview != null) preview.setImageBitmap(ScreenService.preview);
  }

  @Override
  protected void onResume() {
    super.onResume();
    ScreenService.setPhoneVisible(true);
    ScreenService.listener = this::refresh;
    if (status != null) refresh();
  }

  @Override
  protected void onPause() {
    ScreenService.setPhoneVisible(false);
    ScreenService.listener = null;
    super.onPause();
  }

  private void engineSelect(
      LinearLayout host, String label, String key, org.json.JSONArray catalog, boolean evaluator)
      throws Exception {
    java.util.List<String> labels = new java.util.ArrayList<>(), ids = new java.util.ArrayList<>();
    for (int i = 0; i < catalog.length(); i++) {
      org.json.JSONObject item = catalog.getJSONObject(i);
      if (evaluator && item.getString("kind").equals("tiny")) continue;
      ids.add(item.getString("id"));
      labels.add(
          item.getString("label") + (item.optBoolean("available") ? "" : " · install on computer"));
    }
    host.addView(text(label, 14));
    Spinner picker = new Spinner(this);
    picker.setAdapter(
        new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, labels));
    int selected = ids.indexOf(settings.p.getString(key, "stockfish"));
    picker.setSelection(Math.max(0, selected));
    host.addView(picker, new LinearLayout.LayoutParams(-1, dp(48)));
    picker.setOnItemSelectedListener(
        new AdapterView.OnItemSelectedListener() {
          public void onNothingSelected(AdapterView<?> p) {}

          public void onItemSelected(AdapterView<?> p, View v, int at, long id) {
            settings.p.edit().putString(key, ids.get(at)).apply();
            refreshLimits();
          }
        });
  }

  private void refreshLimits() {
    boolean computer = settings.backend().equals("Computer");
    String engine = computer ? settings.engine() : "stockfish";
    boolean human = engine.startsWith("maia"), tiny = engine.startsWith("tiny");
    enable("mode", !human && !tiny);
    enable("seconds", !human && (tiny || !settings.mode().equals("Depth")));
    enable("depth", !human && !tiny && !settings.mode().equals("Time"));
    enable("threads", !human && !tiny);
    enable("skill", engine.equals("stockfish"));
    enable("rating", human || engine.equals("flounder"));
    enable("moves", !tiny);
    if (tiny && engineControls.get("moves") instanceof NumberPicker) {
      ((NumberPicker) engineControls.get("moves")).setValue(1);
      settings.p.edit().putInt("moves", 1).apply();
    }
  }

  private void enable(String key, boolean value) {
    View v = engineControls.get(key);
    if (v != null) {
      v.setEnabled(value);
      v.setAlpha(value ? 1f : .4f);
    }
  }

  private void goBack() {
    if (settingsPage) show();
    else finish();
  }

  @Override
  public void onBackPressed() {
    goBack();
  }
}
