# Phone screen analysis — Android 1.8.5

The app has two sections in one menu:

- **Phone screen** reads a visible chessboard in another phone app, analyzes on this phone and draws arrows. It needs no computer.
- **Computer companion** controls the existing desktop dashboard over trusted Wi-Fi. Its settings and boards remain separate.

## Start

Android 10+ and an ARM64 phone are required for local analysis. Open Phone screen → Settings → Models & downloads. The twelve Tiny bots are built in. Download Stockfish's 99 MB evaluation file and any Maia models you choose. Optional Maia 2/3 files total about 509 MB; LC0 adds about 19 MB, for about 626 MB including Stockfish. Maia 3 79M uses more RAM and CPU than 5M.

Tap Use for moves on a downloaded model card, or select a move engine in Settings. The evaluation engine stays independent. Download completion and settings changes re-analyze the last recognized position, even while the app UI is visible. Press Start, allow full-display screen sharing and, for arrows, Display over other apps. Press Home or Open another app. Keep the complete board visible. Analysis continues while the foreground-service session runs, including after leaving or dismissing the interface. Stop in the app or notification ends capture. Settings save automatically.

Android requests approval for each new capture session. Locking, revoking access, force-stop, protected screens and OS power restrictions can interrupt it. The app does not silently restart screen sharing. It uses no Accessibility service or boot receiver. Screens are processed locally and not saved or uploaded. No autoplay, Study or coaching is included.

A still opening board should be acquired without making a move. **Scan now** clears the current target and retries in the existing sharing session; it does not require quitting the app. Under Help, **Copy diagnostics** includes capture-frame and recognition counts, screen size and the scanner stage, without screenshots or board positions. If no arrow appears, check whether the board preview was recognized, Screen arrows is on, and Only my color is waiting for the bottom side’s turn.

## Times and on-screen evaluation

Tap the timing button on the main Phone screen to edit move and evaluation seconds independently. Saving a move timer while in Depth mode selects Time + depth so the timer actually applies. Detailed depth/limit controls remain in Settings. All four Maia move models show a thinking-time budget too. They produce one main prediction, publish it when ready and use any remaining budget for optional reply passes. At least one pass is allowed to finish, and an in-flight reply can finish after the deadline. Longer time does not deepen or strengthen the main Maia prediction. With Predict replies off, Maia performs one pass. Maia evaluation remains a single value pass with no search timer.

Evaluation Off cancels and unloads the evaluation engine, hides its bars and saves processing power. Screen evaluation is a separate display-only toggle: it can show a passive bar above/beside the board or at a chosen screen edge while other apps remain touchable. It reports the score from White's perspective and updates during Stockfish thinking.

## Local engines

Stockfish 19 supports time, depth, threads, skill and multiple alternatives. Flounder is a labelled Stockfish-based strength mode. All four official Maia exports run through Android ONNX Runtime: Maia 2 Rapid, Maia 3 5M, 23M and 79M. Maia exposes rating, threads, a reply-calculation time budget and continuation controls rather than a fictitious native search-depth setting. Its selected weights load while scanning starts. A bounded 64-position cache holds complete move rankings, so repeating a position, changing the number of alternatives or reaching a predicted position can reuse inference. The cache distinguishes the model, encoded rating, threads and complete FEN, clears on engine close and never stores screenshots. New positions still require a real model pass. The original twelve C# Tiny bots execute inside the APK's .NET Android runtime and provide one recommendation each; they manage their own search depth and receive an adjustable clock budget.

LC0 0.32.1 is an optional on-device CPU engine with a 19 MB network from the official release. It uses neural tree search and can be slower than Stockfish on a phone. Its depth is engine-specific; time limits are the simplest control. The bundled Android executable is built from the included GPL source with Eigen and 16 KB ELF alignment. Desktop LC0 downloads use a Mac universal Accelerate build or the official Windows OpenBLAS archive.

Recommendation and evaluation are independent: for example, Maia moves with a Stockfish bar. Maia values are labelled human expected score. Tiny bots do not supply a numerical evaluation. Model downloads are optional, fixed-hash checked and usable offline after installation. No remote inference or computer pairing is used in Phone screen mode. See `model-tools/README.md` and `tiny-runtime/README.md` for sources, licenses and production build instructions.

**Show moves while thinking** displays the first legal search result from depth one, marked Thinking while the chosen time/depth budget continues. A non-streaming model must finish its first inference first. The completed main move appears before optional reply searches, even when early suggestions are off. **Predict replies** adds a possible continuation: three plies means your move, the opponent's reply and your response. The reply budget limits additional passes, not the primary move. **Steady arrows** reduces changes while thinking; **Lock move** holds the first suggestion until the position/settings change or Scan now is pressed. **Only my color** uses the side at the bottom. Arrows pass touches through.

## Recognition and testing limits

New-frame callbacks request a read with a hardcoded 24 ms minimum interval and a 32 ms fallback, independent of engine time. Discovery retries are throttled to 120 ms. A smaller discovery pass runs first, retaining the full fallback. Unchanged boards use direct RGBA sampling without full-screen bitmap copies. A retained still frame and cached recognition let startup/rescan confirmation complete without waiting for animation or repeating the neural inference. Recognition and engine inference add processing time; these intervals are not a promise of instant arrows. Scan now resets the target and position. The complete supported board must be visible. Unusual themes, occluded pieces and 3D camera angles can remain unreadable. A fresh midgame image cannot always establish turn or castling rights; use the overrides when necessary. Synthetic automatic discovery was exact for 160/186 fixtures, with 26 rejected and zero accepted incorrectly; this is not universal real-device coverage.

Frequent captures now keep a pending board candidate's original stability timestamp rather than resetting it. Opening-board tests cover retained still captures, frequent polling and both orientations in a phone portrait fixture. Single-move tracking checks all legal single moves before searching for two skipped moves, and UCI thread/hash options are prepared before the first board and reused between positions. These changes do not lower confidence thresholds or engine thinking budgets.

Models → **Test installed engines** performs actual inference and legal-move checks on the phone without screen-sharing permission. Stop screen analysis before running it. Host checks and component previews do not prove physical A35 installation, JNI performance, capture, overlay pass-through or background longevity. Those remain device tests for this APK.

## Updates

The app checks public Android releases independently from the desktop release, normally no more than once per six hours. A manual Check for updates button is on the section picker. Android/browser handles download and installation after your approval. No silent installer or REQUEST_INSTALL_PACKAGES permission is used. Keep normal Android security checks enabled.
