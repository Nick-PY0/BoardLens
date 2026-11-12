# BoardLens Android review packet

Historical candidate status: APK withheld after Google Play Protect blocked the replacement public APK on November 11, 2026. No installation was forced and no protection was disabled. The alert only stated "Harmful app blocked" and "This app may be harmful"; the trigger has not been established. This is not a claim that the warning is a false positive.

- Package: app.boardlens.companion
- Version: 1.5.0, code 7
- APK SHA-256: 5be464f90658e5e1ad322838d46a548259d460b90c339fc263608b2ed3cf7589
- Release signing certificate SHA-256: 0ed23ccc294649b716c3cb21ccae9d153a7b91d40f3fe51bf7355c8e263f2544
- Source: https://github.com/Nick-PY0/BoardLens/tree/1b3760c/mobile/android
- Public release/status: https://github.com/Nick-PY0/BoardLens/releases/tag/v1.1.0
- The public candidate APK asset was removed after the block. Its exact bytes are retained by the maintainer for review.

The source implements an explicitly started MediaProjection foreground service for visible 2D chessboard recognition. The user approves each capture session and can stop from the app or notification. The optional application-overlay window is non-focusable/non-touchable (alpha 0.65). Screenshots are processed locally, not recorded or uploaded. Optional paired-computer inference sends a recognized FEN and chosen limits over the local companion connection. The bundled executable is Stockfish built from the included pinned GPL source. Its optional NNUE file is data, downloaded from the official Stockfish network repository with a fixed SHA-256. ONNX Runtime and the Fenshot tile model have their licenses included.

The release candidate is not debuggable. It declares Internet/network-state, foreground-service/media-projection, notifications and display-over-other-apps permissions. It does not declare an Accessibility service, SMS/contacts/location permissions, notification-listener access, a boot receiver or REQUEST_INSTALL_PACKAGES. The custom APK installer was removed. App updates only check the public GitHub release and open its page. These observations are an initial code/package audit, not a complete security clearance.

Functional evidence: GitHub CI has 181 desktop tests passing, Android release/debug builds and four JVM rule tests; emulator development tests cover recognition, legal engine moves, live updates, touch-through arrows, landscape/flip, Stop, and separate computer-engine inference. Physical devices were not tested. The normal signed-APK install failed at Play Protect, so no successful release upgrade or data migration is claimed.

Google's official guidance describes review and the appeal route:
https://developers.google.com/android/play-protect/warning-dev-guidance
https://support.google.com/googleplay/android-developer/answer/2992033?hl=en

No appeal has been submitted. Any message to Google needs the owner's authorization and review of this packet. Do not change identities/signatures or disable protections to evade the block.

The blocked candidate corresponds to source commit 1b3760c. Android 1.7.0 is a later, separately signed build with local Maia and original Tiny engines. It preserves this package identity and release certificate. Host/model tests and the complete APK build pass; the exact new APK has not been installed or tested on the physical A35, and no successful Play Protect review or clearance is claimed. The owner will perform normal installation and device testing. See mobile/TEST-REPORT.txt.
