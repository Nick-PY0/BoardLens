# On-phone Maia models

BoardLens performs inference on Android with ONNX Runtime 1.24.3. No computer or inference server is needed. Four optional float32 models are downloaded separately. The APK pins their byte counts and SHA-256 hashes in `app/src/main/assets/engines/models.json`.

## Source and licenses

- Maia 2: CSSLab/maia2 at `67bee6ce7e2f264344fe6d2026a2e18c76a82efa`, MIT. Official `rapid_model.pt` weights.
- Maia 3: CSSLab/maia3 at `1e13597c42d4858b7cfd7cfdae01e297263364b2`, AGPL-3.0. Official Hugging Face `UofTCSSLab/Maia3-5M`, `Maia3-23M`, and `Maia3-79M` checkpoints, each named `maia3-<size>.pt`.
- Exact input checkpoint hashes, converted hashes, exporter versions and parity cases: `app/src/main/assets/engines/model-provenance.json`.
- License texts ship in `app/src/main/assets/engines/licenses/`. Upstream source archives and the export script accompany the public `phone-models-v1` release.

## Reproduce

Use Python 3.12, PyTorch 2.15.0, ONNX 1.23.2, ONNX Runtime 1.31.1, numpy, python-chess, einops, pandas and PyYAML. Install each pinned upstream package in its own environment. The conversion tool takes its package directory explicitly:

```sh
python export_maia.py --kind maia3-5m --package-path /path/to/site-packages --checkpoint /path/to/maia3-5m.pt --out /path/to/output
```

Repeat for `maia3-23m`, `maia3-79m`, and `maia2`. The exporter uses ONNX opset 18, batch size 1 and float32. RMSNorm is expressed with equivalent primitive operations; MultiheadAttention's native fast path is disabled for export. It writes the vocabulary, input fixtures, provenance and parity report. It checks the legal top move against the official PyTorch model in 39 position/rating cases per model (156 total), including Black orientation, castling, en passant and promotion.

Maia 3 repeats the current board tokenization for eight frames, matching the official UCI adapter when no reliable history is available. It does not invent past boards. Maia is one-pass human-move prediction; search depth and a precise playing-strength Elo are not provided by the model. The UI exposes rating, CPU threads and a separate continuation length/budget instead. Maia values are labelled human expected score, not Stockfish centipawns or win probabilities.
