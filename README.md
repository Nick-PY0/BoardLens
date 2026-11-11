<p align="center"><img src="docs/brand/banner.png" alt="BoardLens" width="660"></p>
<p align="center"><strong>Your best move. On every screen.</strong><br>Open-source chess cheating and analysis software for desktop and Android.</p>
<p align="center"><a href="https://github.com/Nick-PY0/BoardLens/releases/latest"><strong>Download the first public release</strong></a> · <a href="#features">Features</a> · <a href="#phone--tablet">Mobile</a> · <a href="docs/ENGINES.md">Engines</a></p>
<p align="center"><img alt="License GPL-3.0" src="https://img.shields.io/badge/license-GPL--3.0-173d2b?style=flat-square"> <img alt="Mac and Windows" src="https://img.shields.io/badge/desktop-macOS%20%7C%20Windows-173d2b?style=flat-square"> <img alt="Android companion" src="https://img.shields.io/badge/mobile-Android%208%2B-91dfb4?style=flat-square"></p>

BoardLens sees a supported chessboard on your computer, follows its moves and brings engine recommendations, explanations and click-through arrows to your screen. Prefer a clean desktop? Put the interface on your phone while your computer keeps scanning and thinking.

No paid AI subscription is required. Normal recognition and engine analysis run locally after setup. You choose the engine, strength, thinking budget and how much guidance appears.

## See it in action

**Desktop on macOS — the shared Mac/Windows interface**

![BoardLens desktop with engine lines, candidate arrows and evaluation](docs/images/desktop-mac.png)

<p align="center"><img src="docs/images/android-boards.png" alt="Android companion showing the board and evaluation" width="310"> <img src="docs/images/android-analysis.png" alt="Android move analysis" width="310"></p>
<p align="center">Android companion, captured in an emulator. Real app screens, not design mockups.</p>

> **Android APK status:** The development APK is temporarily withheld after Play Protect blocked the emulator install. The browser companion and mobile source remain available. Android download/install testing is under review.

## Download & start

Get the files from [Releases](https://github.com/Nick-PY0/BoardLens/releases/latest).

| Device | Download | Start |
| --- | --- | --- |
| Mac | `BoardLens-Mac-Windows.zip` | Extract, then open **Start BoardLens.command**. Allow Screen Recording when needed. |
| Windows | `BoardLens-Mac-Windows.zip` | Install 64-bit Python 3.12, extract, then open **Start BoardLens.bat**. |
| Android | Phone browser for now; APK temporarily withheld | Open the desktop companion address on the same Wi-Fi. |
| iPhone / iPad | Phone browser, or unsigned iOS source ZIP | Open the desktop companion address. Native source needs Xcode and your signing setup. |

The desktop launcher creates its Python environment and prepares official Stockfish. Optional engines download only when you choose them. The portable desktop ZIP is Python source with launchers, rather than a signed native installer. The Android APK is a locally signed development distribution.

1. Open a complete supported board on your computer.
2. **Board → Read from → Computer screen**; choose a display or all displays.
3. Press **Scan now**, then enable **Auto suggest** to follow moves.
4. Set your engine and limits in **Engine**. Use **Arrows** to control what appears.

## Features

| Feature | What you get |
| --- | --- |
| Automatic screen reading | Finds supported flat 2D boards, without manually selecting an area. Monitor selection and all-display discovery. |
| Fresh scan | Scan now cancels stale work and reads the visible position again. |
| Three-board analysis | Up to three independent tracked positions, engine sessions and recommendations. Cards appear or disappear as boards change. |
| Target lock | Keep one board selected while switching apps; missing or covered pixel targets pause. |
| Orientation detection | Detect the bottom color and optionally show suggestions only for your side. Turn overrides handle uncertain positions. |
| Candidate moves | Show 1–10 recommendations when the selected engine supports them. Rank filters, colors and candidate count control the arrows too. |
| Opponent continuations | See the opponent's predicted reply after a candidate, separately labelled from current-turn recommendations. |
| Plain-language moves | Read “Bishop to f4” alongside SAN, continuation lines and move explanations. |
| Evaluation | Signed White-perspective score, advantage text, mate scores and a board-height evaluation bar. It is not a calibrated winning percentage. |
| Passive screen overlay | Candidate and reply arrows let mouse clicks through. Toggle overlays independently of scanning. |
| Steady arrows | Keep calculating while smoothing changing recommendations. Lock move can hold one suggestion until the board changes or you rescan. |
| Threat highlights | Estimated material-risk rings, optional attacked-square dots and legal mate-in-one targets. |
| Engine controls | Manual engine selection, threads, hash memory, supported strength controls, time/depth/adaptive budgets and early results. |
| Playing styles | Balanced, aggressive, defensive and human-like candidate selection where supported. Maia uses trained human-move models. |
| Engine comparison | Compare 2–3 selected providers on the same position. |
| Optional engine library | Choose individual engines, lightweight downloads or larger neural models. No silent switching or model downloads. |
| Named presets | Quick and Deep presets plus your saved engine/arrow configurations. |
| Position history | Previous/Next pauses live tracking; Resume live returns to the current board. |
| Local Practice board | Load/copy FEN, move pieces, undo and manually play one engine move. |
| Screenshot input | Analyze a supported complete board from an image, including phone uploads. |
| Keyboard shortcuts | Custom shortcuts for suggestions, scanning, arrows, history and Stop. Global shortcuts depend on OS permissions. |
| Clean layout | Compact/expanded desktop views, large board and evaluation, full analysis view and adjustable text size. |
| Persistent settings | Preferences save automatically; phone edits sync back to desktop. Copy actions show feedback. |
| Searchable Help | Sectioned offline guides, full questions, related phrases and common typo matching. |
| GitHub updates | Desktop **Board → App → Check for updates**. Android has an update button on its connection screen and in **Controls**. |

### Themes and 3D

- **2D screen scanning** works independently of the browser connection, for supported artwork.
- **Optional browser reader:** Chess.com/Lichess board data is read independently of its piece artwork. Supported Chess.com 3D boards use projected arrow coordinates. Pair the included Chrome/Edge extension under **Optional connections**; keep the chess tab visible. Site changes can require adapter updates.
- **Local 3D chess:** an independent macOS Accessibility reader supports the built-in Chess.app's 64 accessible squares and projected bounds. It does not cover every 3D chess application.
- Browser and Local 3D connections have separate switches and connection/repair status. Standard screen scanning does not require either reader.

### Phone & tablet

Your computer remains the screen reader and engine host. Its window can stay minimized while the phone provides **Boards, Analysis, Settings and Controls**.

- View up to three boards, candidate arrows, evaluation, explanations and engine comparison.
- Change engine/arrow settings and named presets; edits sync and save on the computer.
- Scan, suggest, Stop, pause/resume, browse history and control local Practice positions.
- Set keyboard shortcuts, upload a screenshot, copy a FEN/configuration and search Help.
- Native Android respects system bars, camera cutouts and the keyboard. Update directly from GitHub through Android's installer.
- Any reachable phone/tablet browser can use the same local companion page. The native iOS wrapper is source-only and unsigned.

**Connect:** desktop **Phone → Enable phone companion**, then enter the displayed computer address and six-digit code on the phone. Use the same trusted local network. Keep the computer awake. Restarting the companion requires its new pairing code.

## Engines

**Stockfish, Maia-3 (5M / 23M / 79M), Maia-2 Rapid, Flounder, Custom UCI**, and twelve optional Tiny Chess Bots. [See engine names, reference ratings and supported controls →](docs/ENGINES.md)

Different engines expose different capabilities. Maia predicts human moves; Tiny bots provide one chosen move without a numerical evaluation or alternative ranked lines. The UI disables unsupported controls.

## Updates

Updates are manual. Desktop verifies the release checksum, restarts, preserves the Python runtime and user data, and keeps rollback copies. Android verifies the checksum, package identity, version and signing certificate, then uses the normal Android confirmation screen. Nothing installs silently. [Update and release details →](docs/UPDATES.md)

The first public release is **v1.0.0**, containing desktop build **2.11.0** and Android build **1.4.0**. These separate build numbers are recorded in the update manifest.

## What is verified

The included validation report records **174 passing automated tests on macOS**, native Mac layout checks and Android-emulator checks. Windows and physical Android/iOS devices have not been tested for this release. The fixed screen-polling target is 75 ms; recognition, engine thinking, display capture and network time still affect end-to-end latency. Current native OS pixel capture has not been reverified; fixture tests are not proof of current capture permission/behavior.

Pixel reads need a clear board and cannot always recover turn, castling or en-passant history. Use exact FEN or a supported direct reader when that metadata matters. Threat checks and engine explanations are estimates. There is no autoplay, stealth/anti-detection guarantee, Study, coaching, puzzles or game-journal feature in this release. Use assistance where your game mode permits it.

## Build & contribute

See [CONTRIBUTING.md](CONTRIBUTING.md). The source is organized into `desktop/` and `mobile/`; branding and real UI screenshots are in `docs/`.

GPL-3.0-or-later. Bundled recognition models, artwork and other components retain their notices in [desktop/THIRD-PARTY.txt](desktop/THIRD-PARTY.txt). BoardLens is not affiliated with Chess.com, Lichess or the engine authors.
