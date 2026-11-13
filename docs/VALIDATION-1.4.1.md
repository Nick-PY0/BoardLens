# BoardLens 1.4.1 validation

Desktop 2.16.1 and Android 1.8.4 (code 14), November 12, 2026.

- Desktop: 203 tests passed with pinned Stockfish 19, including evaluation interpolation, no midpoint reset during refresh, and time/depth availability for every catalog entry.
- Native desktop builds: Windows x64, Mac Intel and Mac Apple Silicon passed GUI startup, local Stockfish legal-move checks and optional LC0 checks in GitHub Actions run 43333171840.
- Android: 57 unit/integration tests passed, zero skipped, with all four real Maia model files and the real Stockfish executable supplied; release lint and complete .NET APK build passed. Cancellation, immutable search settings, update progress/cancellation/cache, and retained evaluation fill have regressions.
- All 12 Tiny bots passed 72 host legal/terminal checks, 36 short-budget checks matching the reported e4/e5/Nf3/Nc6 position, cancellation, and a managed-memory ceiling. Peak live managed memory was below 20 MiB in this test; total Android process memory is larger.
- Android 16 ARM64 emulator: all 19 engines passed actual device execution through the full .NET/Java app: Stockfish, LC0, Flounder, Maia 2, Maia 3 5M/23M/79M, and all 12 Tiny bots. No engine was skipped or silently substituted.
- Live emulator screen: Boychesser at 0.3 seconds, evaluation off, continuously recognized an independent offline QA board, rendered primary/reply arrows and followed board changes. A real optional LC0 download ran as a second foreground service; capture remained active and arrows updated after download completion.
- TinyHugeBot's old packed assembly reproduced a native Mono SIGABRT. Its submitted payload is now recovered as C# and compiled normally. The recovery recipe and MIT provenance are included; no runtime assembly decoder or resolver remains. Six bots use bounded mobile hash tables, which can affect their strength relative to competition ratings.
- Release APK: existing signing identity retained; ZIP and every packaged ARM64 native library checked for 16 KB alignment. No private keys, user settings, frames or pairing information are included.

These checks do not establish physical Samsung A35 performance, every board theme, long-term battery behavior, or removal of the Play Protect flag seen with Android 1.8.3. MediaProjection consent is required for each new sharing session; Android can stop sharing when locked or explicitly stopped. This release does not add autoplay.
