# Updates

Desktop Board → App → Automatic updates is enabled by default. It checks at startup and every six hours, downloads the stable release quietly, verifies SHA-256, and applies the staged archive on the next launch. It does not interrupt live analysis. Turn the toggle off for manual updates. Check for updates still offers Download and restart.

The portable updater validates the complete owned-file manifest and paths, preserves the Python runtime and user data, backs up replaced files, and rolls back on failure. A queued archive is hash checked again before application. Native `.app` and `.exe` builds use the same updater in their private application directory and restart without Terminal; their bundled runtime and original app bundle stay intact. Download a new native ZIP when a runtime/platform upgrade is needed.

Android's section picker has Automatic update checks and Check for updates. It opens the public GitHub release when a newer APK is available. Android handles downloads and installation. BoardLens has no custom APK installer or REQUEST_INSTALL_PACKAGES permission. Nothing silently installs. A withdrawn or missing APK is reported as unavailable.

The release APK is not debuggable. Android 9+ can migrate from the earlier development signing key to the release key using an APK v3 signing lineage; keep application data during an update. Older devices use the legacy signature supported by the APK. Signing keys and passwords are not in this repository. No updater downloads executable engine plugins on Android: the installed Stockfish executable is bundled, and its optional network file is data with a pinned SHA-256.

The earlier development APK was blocked by Play Protect and withdrawn. Do not bypass that protection. A development build or passing functional tests is not proof of security clearance; see the current release notes for replacement testing status.
