# Engines

Downloads are optional and selected manually. Tiny Bot ratings are tournament reference ratings, not guaranteed human playing strengths.

| Engine | Capability |
| --- | --- |
| Stockfish | Full/skill/Elo strength; time/depth/adaptive search and MultiPV. |
| Maia-3 · 5M human model | Trained human-move prediction; optional model and runtime. Target rating is not guaranteed playing strength. |
| Custom UCI | Your installed UCI executable; capabilities depend on its options. |
| Maia-2 · Rapid human model | Trained human-move prediction; optional model and runtime. Target rating is not guaranteed playing strength. |
| Flounder · Stockfish-based | Stockfish-based sampled-move selection; approximate target rating. |
| The CopyCat | Reference rating 192. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| Bongcloud Enthusiast | Reference rating 307. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| WhateverBot | Reference rating 677. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| applemethod-orz | Reference rating 1085. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| Squeedo | Reference rating 1276. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| 200 Tokens Monstrosity | Reference rating 1569. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| Game Tech Explained | Reference rating 1713. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| Electric Shockwave Gambit | Reference rating 2001. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| King Gambot IV | Reference rating 2172. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| NNBot | Reference rating 2246. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| TinyHugeBot | Reference rating 2513. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| Boychesser | Reference rating 2772. One chosen move; no evaluation, search-depth controls or alternative ranked moves. |
| Maia-3 · 23M model | Trained human-move prediction; optional model and runtime. Target rating is not guaranteed playing strength. |
| Maia-3 · 79M model | Trained human-move prediction; optional model and runtime. Target rating is not guaranteed playing strength. |

Stockfish styles rerank close candidates where supported; these are GUI selection styles. The evaluation bar uses the strongest searched score even when the strength-limited recommendation differs. Maia scores describe human-game outcome estimates. Large Maia models download separate runtimes. Comparison can run two or three providers.

Attributions and pinned upstream references are in `desktop/THIRD-PARTY.txt`.

## Android 1.8 local engines

Phone screen analysis needs no computer. Stockfish, Maia 2, all Maia 3 sizes, Flounder strength mode, LC0 and the twelve original Tiny bots run on the phone. Tiny bots are built in; neural-model data downloads are optional. Computer companion remains a separate desktop dashboard. [Phone setup, model sizes, controls and device-test limits →](../mobile/android/PHONE-SCREEN.md)

LC0 0.32.1 is available for desktop and Android as an optional CPU engine/network download. The default network is 791556 from the official release; no GPU is required. It can be slower than Stockfish. Recommendation and evaluation selection remain independent.
