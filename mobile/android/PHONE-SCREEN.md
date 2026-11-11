# On this phone (source preview)

Android has two independent sections: **On this phone** reads a board in another phone app; **Computer companion** controls boards on a paired Mac/Windows computer. Phone settings use their own preferences and never change desktop settings.

Phone mode requires Android 10+ and an arm64 device. Download Stockfish's optional 98,511,183-byte model, press Start, approve full-screen capture, and open a complete 2D board. Allow Display over other apps for passive, touch-through arrows. Stop from the app or its ongoing notification. No recording is saved. No Accessibility permission or boot receiver is used. Android requests capture permission for each session.

Recognition runs locally with the MIT Fenshot tile model. Only flat, unobstructed supported 2D boards are currently recognized. Pixel recognition cannot prove whose turn it is on a midgame first scan: select the side to move when necessary. Orientation can be inferred or overridden. Castling rights are known at a starting position and tracked through observed legal moves; a fresh midgame scan does not guess them.

**On phone engines:** native Stockfish 19 (time, depth, threads, skill and multiple candidates). A separate maximum-strength Stockfish session scores the bar. CPU architecture and Android version support are checked before execution.

**Computer engines for phone positions:** first pair Computer companion, then choose Computer under Phone engines. This sends only a recognized FEN and this section's chosen limits/engine IDs to the paired computer. Stockfish, installed Maia-2 / Maia-3 models, Flounder, Tiny bots and custom UCI providers use separate desktop sessions without changing the desktop tracker or settings. Tiny bots supply one candidate and no numeric evaluation; choose a separate evaluator. These engines are computer-backed, not native Android ports.

The bundled Stockfish executable is built from the corresponding source archive in `engine-source`, GPL-3.0. Rebuild with `engine-source/build-android.sh` and an Android NDK r27+. NNUE download: official-stockfish/networks `nn-1a298aa575a0.nnue`, SHA-256 `1a298aa575a085434d29027978dc36867fe9c5bcea9376654b7a8eba1e52dfc2`. The download contains evaluation data, not executable code. The Fenshot model and its MIT notice are bundled in assets. ONNX Runtime Android is MIT licensed.

Automatic update checks can be switched off on the section picker. They open the public release when an APK is available; Android controls download/installation. BoardLens does not request permission to install other packages. Play Protect blocked both the development APK and the replacement release candidate; APK distribution is withheld. a successful development build is not security clearance.
