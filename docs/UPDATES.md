# Updates and releases

## Desktop

**Board → App → Check for updates** checks the latest stable release of `Nick-PY0/BoardLens`. A release must include `boardlens-update.json` and `BoardLens-Mac-Windows.zip`. The manifest identifies the desktop build version and SHA-256 digest.

Download and restart verifies the archive before changing any application file. A separate helper waits for BoardLens to close, validates its file list, blocks path traversal/runtime replacement, stages the archive and applies owned files. User settings, keys and models are outside the application folder. `.venv` and unowned local files stay intact. Failed writes restore changed files from the backup. Previous application files and the update log live under the BoardLens application-data `updates` directory.

A standard portable, writable installation is required. Review `last-update.txt` if installation fails; you can always extract the release ZIP to a new folder and use the same application-data directory.

## Android

**Check for app updates** is available on the connection screen and in companion **Controls → Update Android app**. The app compares the manifest's Android version code. APK downloads are pinned to this repository's release URLs. SHA-256, package name, version and signing certificate must match before opening the installer.

Android may ask you to allow installation from BoardLens. Grant it only if you want the update, return to BoardLens and confirm installation in Android. Existing connection preferences remain. A changed signing key cannot update an existing installation.

## Publishing the next release

Build and test desktop and Android first. Keep the Android signing key private and use the same key for every distributed update. This initial APK uses the existing local development signing identity; CI debug builds have a different identity and must not replace published update assets.

Use `python tools/package_release.py` to create archives and `boardlens-update.json` in `dist/`, then upload all files to a stable GitHub release and mark that release Latest. Never edit an already published archive without regenerating its manifest/checksums. The release tag and desktop/Android build versions are intentionally separate.

There are no automatic background installs. iOS updates require the user's own signing/distribution setup.
