# Third-Party Notices

This file summarizes the notable third-party components selected for the initial implementation. Verify exact transitive licenses before publishing release binaries.

## PaddleOCR

- Project: https://github.com/PaddlePaddle/PaddleOCR
- License: Apache License 2.0
- Use: Full-frame OCR pipeline.

## PaddlePaddle

- Project: https://github.com/PaddlePaddle/Paddle
- License: Apache License 2.0
- Use: Default PaddleOCR inference backend on macOS CPU.

## ONNX Runtime

- Project: https://onnxruntime.ai/
- License: MIT
- Use: Optional alternate OCR inference backend for packaging/performance comparison.

## PyAV and FFmpeg

- Project: https://github.com/PyAV-Org/PyAV
- License: BSD-3-Clause for PyAV.
- Use: Video decoding and presentation timestamps.
- Note: PyAV wheels bundle FFmpeg. Before distributing binaries, verify the exact wheel build, bundled FFmpeg configuration, and applicable LGPL/GPL obligations.

## PySide6 / Qt for Python

- Project: https://doc.qt.io/qtforpython-6/
- License: LGPLv3/GPLv3 or commercial license.
- Use: macOS desktop GUI.
- Note: Distribution must preserve LGPL compliance, including notices and the ability to replace LGPL libraries where required.

## PyInstaller

- Project: https://pyinstaller.org/
- License: GPLv2-or-later with bootloader exception.
- Use: macOS `.app` packaging.

## Pillow

- Project: https://python-pillow.org/
- License: Historical Permission Notice and Disclaimer.
- Use: Screenshot writing and annotation.

## RapidFuzz

- Project: https://github.com/rapidfuzz/RapidFuzz
- License: MIT
- Use: OCR text similarity for temporal tracking.

## PySceneDetect

- Project: https://github.com/Breakthrough/PySceneDetect
- License: BSD-3-Clause
- Use: Adaptive scene-cut and fade detection for priority sampling.
