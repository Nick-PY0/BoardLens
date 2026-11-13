# Samsung A35 device check

November 12, 2026. Android 1.8.4 (code 14) was installed over 1.8.3 on a physical Samsung A35 through authorized ADB access, without uninstalling BoardLens or clearing its data.

The first engine check passed all 12 included Tiny bots; optional engine data was not installed at that point. Once the optional data was available, a second check passed all 19 engines: Stockfish, LC0, Flounder, Maia 2, Maia 3 5M/23M/79M and all 12 Tiny bots. Each returned a legal move for the app's diagnostic position. This is not a claim about every chess position or all-day stability.

Live MediaProjection scanning was then checked with the phone's selected TinyHugeBot, a 0.1-second budget and evaluation off. BoardLens recognized an independent offline 2D test board and drew primary/reply arrows. Manual taps through the arrow moved the white knight from g1 to f3; the test board reported Move accepted and BoardLens updated its arrows for Black's turn. The capture service remained in the foreground. No new BoardLens process exit was recorded during the check.

The test session was stopped and the temporary test-board app removed afterward. BoardLens, its downloaded model data and its selected engine settings were retained. Screenshots and device identifiers were not published.
