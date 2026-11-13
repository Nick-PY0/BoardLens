# Choose how browser boards are read

Desktop 2.16.2 adds a visible Board → Computer screen → Use browser extension toggle.

Off uses normal screen scanning. On prefers the paired extension for visible Chess.com/Lichess boards, including standard 2D themes and supported 3D boards. Screen scanning remains the fallback when no extension board is available. Local 3D chess remains a separate reader.

Switching readers clears stale observations, arrows and browser target locks, then refreshes a running scan. It does not start a stopped scanner. The choice saves automatically. Pairing and connection status remain under Optional connections.

Validation: 206 desktop tests, including actual worker-path checks for extension priority, disconnected fallback, switching, saved preference and stopped-state behavior. Android 1.8.4 is unchanged; it was installed over 1.8.3 on the connected Samsung A35, and all 12 included bots passed the device engine check. Seven optional engines were not installed at the time of that check.
