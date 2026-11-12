# Recognition development

These tools fetch reference artwork locally and generate labeled screen-space
contexts for the small BoardLens context classifier. Downloaded artwork and
large datasets are not included in Git or releases. Source artwork keeps its
original licenses. Lichess's inventory excerpts retain the accompanying Lila
license. The Chess.com index is an inventory hint; artwork URLs point to
Chess.com's own CDN. An index does not establish live support for every theme.

Use an isolated Python 3.12 environment with PyTorch, numpy, Pillow, resvg-py,
onnx, onnxruntime and opencv-python-headless. Run `fetch_assets.py`,
`prepare_contexts.py`, then `EPOCHS=6 python train_context.py` and
`python finetune_context.py`. `BOARDLENS_CORPUS` selects the dataset directory.
`CONTEXT_CHECKPOINT=context-net-7.pt python audit_context.py` exports the
selected checkpoint and audits cropped classification. Checkpoint 7 had the
best held-out validation accuracy in the recorded run. GPU execution is not
bit-identical across platforms. Training scripts/network weights are supplied
under the project's GPL-3.0 license; no pretrained network was used here.

An audit of already-cropped boards is not an automatic detection test. Use the
separate Android component harness with locally generated fixtures to test
actual discovery, both orientations and uncertain results. Do not publish
local reference artwork or private companion state with test artifacts.
