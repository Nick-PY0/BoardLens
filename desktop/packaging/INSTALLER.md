# Mac drag installer

Build the native bundle first, then install `dmgbuild==1.6.7` in the build
Python environment and run:

```
python packaging/build_dmg.py --app /path/to/BoardLens.app --out native-dist
```

The DMG opens a fixed Finder layout with BoardLens, an Applications link and a
short drag instruction. Its code signature and disk image are verified during
packaging. It requests no administrator password or permission grant. Drag the
app into Applications, eject the installer, then open BoardLens there.
The app displays installation guidance if opened directly from the mounted DMG.
Settings remain in Application Support and are not stored inside the app.

BoardLens checks Accessibility quietly. Only pressing the Accessibility
settings button can request it; restoring a saved local 3D reader preference
never opens an OS prompt. Accessibility is for the local 3D reader, not ordinary
2D screen capture or the app's cooperative global shortcuts. Screen Recording
is a separate OS permission. Different copies/signatures can have separate
macOS grants; use the installed Applications copy consistently.

The native builder reuses the single Developer ID Application identity in the
local Keychain. Select one explicitly with `--sign-identity NAME_OR_FINGERPRINT`
or `BOARDLENS_CODESIGN_IDENTITY` when several exist. Private keys stay in the
Keychain. Certificate-backed builds keep a compatible designated requirement
across updates, so permissions can remain attached to the installed app.
Builds without a Developer ID are labelled `ad-hoc` in their metadata. Changing
an ad hoc native build can require reauthorizing OS permissions; an ordinary
source update does not replace the native host or its signature.

When migrating from an older temporary signature, quit BoardLens, remove the
old BoardLens entry in Privacy & Security → Accessibility, add
`/Applications/BoardLens.app`, and enable it. Reopen BoardLens. Apply the same
repair to Screen Recording only if that permission also remains denied.
BoardLens never edits or resets the macOS permission database.
