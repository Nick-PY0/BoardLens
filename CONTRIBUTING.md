# Working on BoardLens

Use Python 3.12. From `desktop/`, create a virtual environment, install `requirements.txt` and `pytest`, then run `python -m chess_helper`.

```sh
python -m pytest -q
```

Tests isolate their application-data directory. Optional engine downloads are not part of normal tests. Set `STOCKFISH_EXECUTABLE` to a local Stockfish binary for engine checks. GUI tests use Qt's offscreen backend; native Mac screenshots are checked separately. Native 3D reading is macOS-specific.

Android: open `mobile/android` in Android Studio or set `ANDROID_HOME` and run `./gradlew :app:assembleDebug`. Java 17+ and Android SDK 36 are required. Keep signing keys, local SDK paths, credentials and personal screenshots outside Git.

The companion UI is served from `desktop/chess_helper/assets/phone`. Mobile settings must pass through the Qt-owned command bridge; HTTP threads must not read widgets directly. Preserve passive overlays, user-controlled engine limits and the independent 75 ms screen-polling target.

When changing updates, run the updater tests, check archive traversal rejection and rollback, and use isolated application copies. Keep existing user data and optional engines intact.
