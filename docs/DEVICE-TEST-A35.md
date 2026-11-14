# Samsung A35 device check

November 12, 2026. Android 1.8.4 (code 14) was installed over 1.8.3 on a physical Samsung A35 through authorized ADB access, without uninstalling BoardLens or clearing its data.

The first engine check passed all 12 included Tiny bots; optional engine data was not installed at that point. Once the optional data was available, a second check passed all 19 engines: Stockfish, LC0, Flounder, Maia 2, Maia 3 5M/23M/79M and all 12 Tiny bots. Each returned a legal move for the app's diagnostic position. This is not a claim about every chess position or all-day stability.

Live MediaProjection scanning was then checked with the phone's selected TinyHugeBot, a 0.1-second budget and evaluation off. BoardLens recognized an independent offline 2D test board and drew primary/reply arrows. Manual taps through the arrow moved the white knight from g1 to f3; the test board reported Move accepted and BoardLens updated its arrows for Black's turn. The capture service remained in the foreground. No new BoardLens process exit was recorded during the check.

The test session was stopped and the temporary test-board app removed afterward. BoardLens, its downloaded model data and its selected engine settings were retained. Screenshots and device identifiers were not published.


## Native-app follow-up — November 13, 2026

Android 1.8.5 (code 15) was installed over 1.8.4 with saved TinyHugeBot, 0.1-second move time and evaluation off retained. The untouched native Chess.com bot starting-board screenshot was correctly recognized by the production Android reader on the host. This is a screenshot-recognition check, not proof of live arrow delivery.

During inspection of the owner's online-game screen in Chess.com Android 4.10.27, the game window had `FLAG_SECURE` (window flags `0x81812180` include `0x2000`). Its captured content was black while system bars remained visible. Android's secure-window behavior withholds those pixels. Faster classification cannot recover a board from that capture. The earlier bot opening screenshot was readable; this does not establish that all bot/game screens are capturable. No app protection was modified or bypassed.

A capture session was also observed inactive, with no new BoardLens process crash. The cause of that stop was not established while the phone was being used interactively. USB disconnected before the 1.8.6 build and Chrome follow-up could be checked on the physical phone. No human match, invitation or chess move was submitted by the test operator. Raw phone screenshots, account names and device identifiers are not published.

## Android 1.8.7 follow-up

The signed public 1.8.7 APK (code 17) upgraded 1.8.5 without clearing data. The selected TinyHugeBot, 0.1-second move budget and disabled evaluation engine were retained. An independent offline opening board was recognized without moving a piece, and primary and predicted-reply arrows appeared on it. Hiding/revealing and relocating the board also triggered reacquisition while capture stayed active.

Three warm hide/reveal trials measured 0.706, 0.503 and 0.857 seconds (median 0.706) from the fixture button tap to BoardLens's recognition-notification update. Device timestamps were used, and the first diagnostic query was delayed two seconds to reduce polling interference. The interval includes input delivery, WebView paint, capture, confirmation and notification overhead; it does not measure engine search or arrow latency. Relocating the board took 0.624 seconds by the same notification timestamp method. The initial screen-sharing trial was observed within a 1.281–1.717-second host polling interval, including sharing startup. There was no old-version physical-phone baseline.

The QA-only fixture needed system-bar/cutout insets: Samsung's three-button navigation overlapped its bottom Hide control and intercepted a test tap. That harness layout was fixed, rebuilt, installed and visually checked; no production APK code changed during this device check.

USB disconnected before the physical Chrome test, notification Scan now/Stop, flipped/highlighted board-arrow check, move-through-overlay update and final process-exit comparison could be completed. The capture service was still foreground at its last connected inspection. A flipped fixture screenshot alone did not verify arrows in that orientation. The temporary `app.boardlens.qatarget` test app remained installed at disconnect; final cleanup is pending reconnection. No claim of crash-free or all-day operation is made from this incomplete session.

Anonymized measurements and coverage are in [the A35 timing report](recognition/android-discovery-1.8.7-a35.json). Raw phone screenshots, notification history, account names and device identifiers are excluded.

## Resumed check — November 14, 2026

The same 1.8.7 APK remained installed. The on-phone engine check passed all 19 installed engines, zero failed or missing: Stockfish, LC0, Flounder, Maia 2, Maia 3 5M/23M/79M and the 12 Tiny bots. Each returned a legal move for the app's diagnostic position; this does not test all positions or imply all engines stream early results.

An untouched cBurnett offline board produced primary/reply arrows. A g1-f3 move made with taps through the overlay was accepted; suggestions changed to Black and its predicted White reply. Notification Scan now refreshed visual tracking without ending capture or showing another sharing-consent dialog. The phone-screen Stop control ended capture normally.

This refresh test exposed a real bug: discarding the confirmed chess state changed Black's turn back to inferred White on the unchanged board after g1-f3. The 1.8.8 candidate retains that state while discarding visual tracking, then validates/synchronizes it against the newly read placement. The regression failed before the fix and passes afterward. All 78 host tests, release lint and the complete signed build pass. The phone rejected the candidate upgrade for insufficient storage; the owner chose to keep testing 1.8.7. The 1.8.8 fix has not been installed or verified on the A35, and is not yet a public release.

On 1.8.7, a flipped offline board was recognized and arrows followed its geometry; correct turn after refresh is not claimed because of the bug above. The untouched Chess.com public analysis board in regular Chrome also displayed arrows. A Chrome drag scrolled the page without completing a chess move, so physical Chrome move-following remains unverified. Animated-highlight recovery and every native/game layout were not established by this session. No human match or invitation was created.

No new process exit was recorded between the resumed baseline and the post-capture check. At final cleanup BoardLens was force-stopped without further UI interaction, the temporary QA app was removed, capture was confirmed inactive (`MediaProjection: null`), and the installed version remained 1.8.7. The force-stop was deliberate cleanup. USB disconnected before the final process-exit query, so no final crash-buffer/all-day claim is made. BoardLens's saved models/settings were not cleared. Raw phone images and identifiers remain excluded from this report.
