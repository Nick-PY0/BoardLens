# Full Android application and original Tiny bots

This .NET for Android project packages the existing Java capture/UI/ONNX implementation with the original C# Chess Challenge bots in one process. No computer is needed. The original source files and commit are recorded in `sources.json`; the framework and bots are MIT licensed.

The adapter disables Bot 303's opponent-GC attack (irrelevant outside the competition), qualifies its math calls, and validates the scripted opening moves in Bots 278/253 before using them when joining an arbitrary screen position. Shared board API calls check cancellation and the clock deadline. Every returned move is validated both in C# and against the Java rules implementation. Exceptions cross the Java bridge as structured errors. They never select a different bot silently. Bots manage their own search depth; the phone supplies the chosen clock budget. Most return one recommendation and have no meaningful numerical evaluation.

## Build the complete APK

Install .NET SDK 10.0.404, its Android workload, Android SDK 36, JDK 17, and NDK 27.1.12297006. Build the pinned Stockfish executable first if it is absent:

```sh
dotnet workload install android
ANDROID_NDK_HOME=/path/to/ndk/27.1.12297006 sh ../engine-source/build-android.sh
dotnet build BoardLens.Android.csproj -c Release -p:AndroidSdkDirectory=/path/to/android-sdk -p:JavaSdkDirectory=/path/to/jdk17
```

The full unsigned package is `bin/Release/net10.0-android/android-arm64/app.boardlens.companion.apk`. Align/sign it with your release key. The SDK-generated `-Signed.apk` uses a development key unless signing properties were configured; it is not the BoardLens release artifact. A Gradle-only APK does **not** include the Tiny runtime and is not the full production build.

```sh
dotnet run --project Host/Host.csproj -c Release
```

The host check covers all 12 bots across 72 legal/terminal-position cases and cancellation. It does not establish Android JNI or physical-device performance. The app's Models → Test installed engines runs actual device inference without requiring screen-sharing access. Android 10+/ARM64 is required for local screen analysis.
