# Install BoardLens

On Mac, download the DMG for Apple silicon or Intel. Open it, drag **BoardLens** into **Applications**, eject the installer and open BoardLens there. Quit an existing copy before replacing it. Saved settings and downloaded engines stay in Application Support.

The installer verifies its disk image and the copied app signature during packaging. It does not change macOS permissions. Screen Recording is required for screen pixels. Accessibility is optional for local 3D reading and is checked without prompting; use Board → App → Permissions to request it explicitly. Keep using the installed copy so grants are associated with the same app.

On Windows, extract the Windows ZIP and open BoardLens.exe. The native launcher opens no Terminal/console window.


Download the matching ZIP from [Releases](https://github.com/Nick-PY0/BoardLens/releases/latest).

- **Apple Silicon Mac:** BoardLens-Mac-AppleSilicon.zip, macOS 14+.
- **Intel Mac:** BoardLens-Mac-Intel.zip, macOS 14+.
- **Windows:** BoardLens-Windows-x64.zip, Windows 10/11 x64.

Extract the ZIP. On Mac, open **BoardLens.app**; you can move it to Applications. On Windows, open **BoardLens.exe** and keep the Resources folder beside it. Pin the app to the Dock or taskbar if desired. No Terminal, command prompt, global Python, pip or Homebrew installation is required.

The first launch shows a preparation window while it verifies and extracts the bundled runtime. Later launches reuse it. Recognition assets and official Stockfish 19 are included, so the basic app works offline. Optional engines/models retain their separate, explicit downloads.

## Existing settings

The native app uses the same BoardLens app-data directory as the source version: `~/Library/Application Support/BoardLens` on Mac, `%LOCALAPPDATA%/BoardLens` on Windows. Settings, models, pairing keys, history and saved presets stay there. Quit the old source version before opening the native app. Subsequent opens focus the already-running app.

## Updates and permissions

Board → App controls automatic updates and Check for updates. Updates replace the private application source, keep the bundled Python runtime and user data, and restart without opening a console. The downloaded Mac bundle itself is not modified. Platform/runtime upgrades may need a new native ZIP.

Screen Recording and Accessibility remain OS-controlled permissions. A new app identity can require you to approve them again in system settings. Mac builds are ad-hoc signed and not notarized; the Windows executable is unsigned. Do not disable OS protections if a download is blocked. The source fallback remains available.

## Build architecture

A small Objective-C Cocoa launcher (Mac) or C# WinExe launcher (Windows) verifies a SHA-256 payload and prepares it under the user's private `BoardLens/native` directory. It runs a relocatable CPython installation, preserving a real Python executable for optional model runtimes. Python helper processes and engines run without console windows on Windows. No administrator access or system Python modification is needed.

From a clean checkout, use Python 3.12 and run:

```sh
python desktop/packaging/build_native.py --work native-work --out native-dist
```

Mac needs Xcode command-line tools and a relocatable standalone Python (the workflow uses uv). Windows needs the standard .NET Framework compiler and Pillow for icon export. The workflow builds and self-tests Windows x64 and Intel Mac; Apple Silicon is built and self-tested on a Mac. Native payloads include the corresponding source and license for Stockfish.

The hidden `--self-test report.json` developer option uses isolated settings, renders the GUI offscreen, loads the actual recognition model and asks bundled Stockfish for a legal move. It does not test OS capture permissions or every optional engine.
