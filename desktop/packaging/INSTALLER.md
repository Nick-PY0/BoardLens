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
