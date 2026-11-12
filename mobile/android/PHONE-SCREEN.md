# Phone screen analysis — Android 1.7

The app has two sections in one menu:

- **Phone screen** reads a visible chessboard in another phone app, analyzes on this phone and draws arrows. It needs no computer.
- **Computer companion** controls the existing desktop dashboard over trusted Wi-Fi. Its settings and boards remain separate.

## Start

Android 10+ and an ARM64 phone are required for local analysis. Open Phone screen → Settings → Models & downloads. The twelve Tiny bots are built in. Download Stockfish's 99 MB evaluation file and any Maia models you choose. Optional Maia 2/3 files total about 509 MB; downloading everything including Stockfish is about 607 MB. Maia 3 79M uses more RAM and CPU than 5M.

Select a move engine and a separate evaluation engine. Press Start, allow full-display screen sharing and, for arrows, Display over other apps. Press Home or Open another app. Keep the complete board visible. Analysis continues while the foreground-service session runs, including after leaving or dismissing the interface. Stop in the app or notification ends capture. Settings save automatically.

Android requests approval for each new capture session. Locking, revoking access, force-stop, protected screens and OS power restrictions can interrupt it. The app does not silently restart screen sharing. It uses no Accessibility service or boot receiver. Screens are processed locally and not saved or uploaded. No autoplay, Study or coaching is included.

## Local engines

Stockfish 19 supports time, depth, threads, skill and multiple alternatives. Flounder is a labelled Stockfish-based strength mode. All four official Maia exports run through Android ONNX Runtime: Maia 2 Rapid, Maia 3 5M, 23M and 79M. Maia exposes rating, threads and continuation controls rather than a fictitious native search-depth setting. The original twelve C# Tiny bots execute inside the APK's .NET Android runtime and provide one recommendation each; they manage their own search depth and receive an adjustable clock budget.

Recommendation and evaluation are independent: for example, Maia moves with a Stockfish bar. Maia values are labelled human expected score. Tiny bots do not supply a numerical evaluation. Model downloads are optional, fixed-hash checked and usable offline after installation. No remote inference or computer pairing is used in Phone screen mode. See `model-tools/README.md` and `tiny-runtime/README.md` for sources, licenses and production build instructions.

**Show moves while thinking** displays early results when available. A non-streaming model must finish its first inference first. **Predict replies** adds a possible continuation: three plies means your move, the opponent's reply and your response. The reply budget limits additional passes, not the primary move. **Steady arrows** reduces changes while thinking; **Lock move** holds the first suggestion until the position/settings change or Scan now is pressed. **Only my color** uses the side at the bottom. Arrows pass touches through.

## Recognition and testing limits

Board polling is hardcoded to 75 ms, independent of engine time. Discovery is throttled to 250 ms. Unchanged boards use direct RGBA sampling without full-screen bitmap copies. A retained still frame lets startup/rescan confirmation complete even if Android supplies no further damaged frames. Recognition and engine inference add processing time; these intervals are not a promise of instant arrows. Scan now resets the target and position. The complete supported board must be visible. Unusual themes, occluded pieces and 3D camera angles can remain unreadable. A fresh midgame image cannot always establish turn or castling rights; use the overrides when necessary. Synthetic automatic discovery was exact for 160/186 fixtures, with 26 rejected and zero accepted incorrectly; this is not universal real-device coverage.

Models → **Test installed engines** performs actual inference and legal-move checks on the phone without screen-sharing permission. Stop screen analysis before running it. Host checks and component previews do not prove physical A35 installation, JNI performance, capture, overlay pass-through or background longevity. Those remain device tests for this APK.

## Updates

The app checks public Android releases independently from the desktop release, normally no more than once per six hours. A manual Check for updates button is on the section picker. Android/browser handles download and installation after your approval. No silent installer or REQUEST_INSTALL_PACKAGES permission is used. Keep normal Android security checks enabled.
