# iOS port feasibility — November 12, 2026

The companion UI, saved settings, chess rules, imported positions, recognition models and engine selection can be ported. Engines must be embedded as in-process libraries/AOT code; the Android executable-launch approach is not an iOS implementation. Maia can use ONNX Runtime or an appropriate native conversion; Stockfish and LC0 need C/C++ library bridges. This is a feasible implementation plan, not an already-built iOS analysis app.

Apple now documents [ScreenCaptureKit on iOS/iPadOS 27](https://developer.apple.com/documentation/screencapturekit), with a system content-sharing picker, permission and appropriate background execution capabilities. Older devices need a different ReplayKit broadcast-extension design. These APIs make user-approved capture possible; they do not establish that this project already supports it.

Android's unrestricted passive screen-arrow window has no equivalent implemented here on iOS. UIKit windows belong to the app's own scenes. A supported first port can show the board, evaluation and arrows inside BoardLens or its own browser, plus the desktop companion. A prototype on real iOS hardware is needed before claiming any system-wide overlay behavior. Do not promise full Android feature parity or imply that background screen capture is silent.

The existing iOS directory is still an unsigned companion wrapper. A real device build needs Xcode and the owner's signing/provisioning setup.
