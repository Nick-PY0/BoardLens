# Isolated component checks

This test harness has no screen-capture permission, overlay permission,
background service, engine or network permission. It renders the production
shared UI components and can read developer-supplied static image fixtures.
It is not a distributable BoardLens app and cannot prove background capture,
installation clearance, or device compatibility.

Build with `./gradlew :qa-components:assembleDebug`. Runtime fixtures live in
`src/main/assets`, which is intentionally excluded from source archives and
Git because it contains local reference artwork and generated test state.
Copy the companion HTML/CSS/JS to `assets/companion` for a WebView layout test.
Provide `fixture-state.json` with the companion state schema. For the reader,
provide `reader-fixtures.json`, a list with `image`, `placement`, optional
`orientation`, and optional `rect` or `corners`; put images in `assets/fixtures`.

The `page` intent extra selects `companion`, `phone`, or `reader`. Reports are
written to the harness's private `files` directory. Do not confuse these
component results with a successful full-app installation or capture test.
