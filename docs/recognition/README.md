# Recognition coverage

The Android reader combines the existing 2D tile classifier with a new
screen-space context classifier. Contexts include the space above a square so
raised piece artwork can be identified. A four-piece projection check retains
the fast 2D path. Homographies map projected squares to arrow endpoints.

The inventory contains 93 piece sets (42 Lichess 2D, 11 Lichess 3D artwork,
40 Chess.com) and 81 board textures. Training uses 92 distinguishable piece
sets, 62 flat textures and 282,624 contexts. Lichess Disguised intentionally
hides identity; its six pieces per color share artwork and cannot be identified
from a fresh screenshot alone.

The selected checkpoint had 99.9236% held-out tile accuracy. In a separate
186-case cropped audit (starting and flipped opening positions), it identified
181 whole boards exactly, accepted 176 under strict confidence thresholds,
and made zero confidently accepted errors. The older classifier covers some
2D misses. Classification of an already-cropped board does not prove discovery
in a live screenshot.

The final Android component sweep tested 186 rendered starting/opening boards across all 93 piece-set entries, with varied board textures and both orientations. It read **160 exactly**, rejected 26 uncertain cases, and accepted **zero wrong positions**. This is partial coverage, not universal support. An experimental relaxed detector accepted shifted seven-file crops; the final reader verifies every outside rank and file and rejects that failure. See [per-style Android discovery results](android-discovery.json).

An inclined synthetic 3D scene remained uncertain. Arbitrary WebGL/real-world 3D cameras, Disguised pieces and occlusions are not verified universal support. Desktop direct readers remain useful when pixels do not contain enough information.

- [Network and corpus metadata](model.json)
- [Cropped context audit](cropped-theme-audit.json)
- [Previous classifier audit](previous-cropped-theme-audit.json)
- [Theme inventory](inventory.json)
- [Reproduction tools](../../tools/recognition/README.md)

Reference artwork is not bundled. Screenshots stay local; optional computer
engines receive only the recognized position.
