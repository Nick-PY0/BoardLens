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
  private PhoneDashboard dashboard;
  private TextView modelNote;
  private final java.util.Map<String, View> engineControls = new java.util.HashMap<>();
  private TextView status, moves, eval;
  private ImageView preview;
  private ProgressBar bar;
  private LinearLayout content;
  private final int bg = MobileUi.BG, fg = MobileUi.FG, accent = MobileUi.ACCENT;
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
    b.setBackground(shape(MobileUi.SURFACE));
    b.setStateListAnimator(null);
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
    settingsPage=false;building=true;
    dashboard=new PhoneDashboard(this,new PhoneDashboard.Actions(){
      public void start(){PhoneScreenActivity.this.start();}
      public void stop(){stopService(new Intent(PhoneScreenActivity.this,ScreenService.class));}
      public void hide(){moveTaskToBack(true);}
      public void scan(){if(ScreenService.running)startService(new Intent(PhoneScreenActivity.this,ScreenService.class).setAction("REFRESH"));else PhoneScreenActivity.this.start();}
      public void settings(){engineSettings();}
      public void help(){showHelp();}
      public void back(){finish();}
      public boolean option(String key,boolean fallback){return settings.p.getBoolean(key,fallback);}
      public void option(String key,boolean value,boolean unused){settings.p.edit().putBoolean(key,value).apply();}
    });
    status=dashboard.status;moves=dashboard.moves;eval=dashboard.eval;bar=dashboard.bar;preview=dashboard.preview;
    inset(dashboard.root);setContentView(dashboard.root);building=false;refresh();
  }

  private void showHelp(){
    new AlertDialog.Builder(this).setTitle("Phone screen analysis")
      .setMessage("Press Start and allow screen sharing. Choose the entire screen to follow boards across apps. Allow Display over other apps for arrows. Then press Home or Open another app. The ongoing notification means analysis is still running; use its Stop action to end it.\n\nAndroid can end capture when you lock your phone, revoke permission or force-stop the app. Protected screens cannot be captured. BoardLens never starts capture without your permission.\n\nKeep the whole board visible. Unsupported themes, 3D angles or hidden pieces may not read. Computer mode sends only the recognized position to your paired computer, not screenshots.\n\nShow moves while thinking displays the first useful result before calculation finishes. Predict replies adds possible opponent and follow-up moves; it recalculates when the actual move differs. A ply is one move by one side. Maia 2/3 use one model pass per position, not search depth. Reply time budget limits extra passes; a running pass may finish after it. Tiny bots use their own coded search and a bot clock budget.\n\nAll settings save automatically. Phone-screen settings are separate from computer companion settings.")
      .setPositiveButton("Got it",null).show();
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
          b.setBackground(shape(on ? accent : MobileUi.SURFACE));
        };
    b.setOnClickListener(
        v -> {
          settings.p.edit().putBoolean(key, !settings.p.getBoolean(key, fallback)).apply();
          paint.run();
        });
    paint.run();
  }

  private void select(String title, String key, String[] values, String current) {
    TextView label=text(title,14);content.addView(label);
    Spinner s = new Spinner(this);
    ArrayAdapter<String> a =
        new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, values);
    s.setAdapter(a);
    engineControls.put(key, s);s.setTag(label);
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
    TextView label=text(title,14);content.addView(label);
    MobileUi.Stepper n=new MobileUi.Stepper(new MobileUi(this),min,max,current,value->settings.p.edit().putInt(key,value).apply());
    engineControls.put(key,n);n.setTag(label);content.addView(n,new LinearLayout.LayoutParams(-1,dp(48)));
  }

  private void decimal(String title,String key,float value,float min,float max){
    content.addView(text(title,14));EditText field=new EditText(this);field.setSingleLine();field.setTextColor(fg);field.setInputType(8194);field.setText(String.valueOf(value));content.addView(field,new LinearLayout.LayoutParams(-1,dp(48)));
    field.addTextChangedListener(new android.text.TextWatcher(){
      public void beforeTextChanged(CharSequence s,int a,int count,int after){}
      public void onTextChanged(CharSequence s,int start,int before,int count){try{float n=Float.parseFloat(s.toString());if(Float.isFinite(n)&&n>=min&&n<=max){settings.p.edit().putFloat(key,n).apply();field.setError(null);}else field.setError(min+" to "+max);}catch(Exception e){field.setError("Enter seconds");}}
      public void afterTextChanged(android.text.Editable s){}
    });
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
    button("‹ Phone screen",this::show);
    content.addView(text("Engines & settings", 24));
    content.addView(text("Recommendations and evaluation are independent.",14));
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
    TextView timeLabel=text("Think time (seconds)",14);content.addView(timeLabel);
    EditText seconds = new EditText(this);
    engineControls.put("seconds", seconds);seconds.setTag(timeLabel);
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
    number("Search depth", "depth", 1, 30, settings.depth());
    modelNote=text("",13);content.addView(modelNote);
    toggle("Show moves while thinking","early",true);
    toggle("Predict replies","predict",true);
    number("Prediction length · plies","prediction_plies",1,12,settings.predictionPlies());
    decimal("Reply time budget (seconds)","prediction_seconds",settings.predictionSeconds(),.1f,60f);
    toggle("Steady arrows","steady",true);
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
    setContentView(scroll);refreshLimits();
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
    if(isFinishing()||settingsPage||dashboard==null)return;
    dashboard.render(ScreenService.running,ScreenService.status,ScreenService.suggestion,ScreenService.evaluation,ScreenService.whiteShare,ScreenService.preview);
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
    if(modelNote!=null)modelNote.setText(human?"Maia 2/3: one pass per position. Adjust prediction length and reply budget below.":tiny?"This bot sets its own depth. Think time is its clock budget.":"Time + depth stops at whichever limit comes first.");
    enable("mode", !human && !tiny);
    enable("seconds", !human && (tiny || !settings.mode().equals("Depth")));
    enable("depth", !human && !tiny && !settings.mode().equals("Time"));
    enable("threads", !human && !tiny);
    enable("skill", engine.equals("stockfish"));
    enable("rating", human || engine.equals("flounder"));
    enable("moves", !tiny);
    if (tiny && engineControls.get("moves") instanceof MobileUi.Stepper) {
      ((MobileUi.Stepper) engineControls.get("moves")).setValue(1);
      settings.p.edit().putInt("moves", 1).apply();
    }
  }

  private void enable(String key, boolean value) {
    View v = engineControls.get(key);
    if (v != null) {
      v.setEnabled(value);
      v.setAlpha(value ? 1f : .4f);
      v.setVisibility(value?View.VISIBLE:View.GONE);
      Object label=v.getTag();if(label instanceof TextView)((TextView)label).setVisibility(value?View.VISIBLE:View.GONE);
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
