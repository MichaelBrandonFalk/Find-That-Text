# Technical Validation

This document records the first validation pass requested before committing to the architecture.

## Current Official Documentation Checked

- PaddleOCR installation: `paddleocr` supports Python 3.8+ for the core package, and the default package covers general OCR and document image preprocessing. Source: [PaddleOCR installation guide](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/installation.en.md).
- PaddleOCR general OCR pipeline: PaddleOCR 3.7 defaults to PP-OCRv6 medium models; the pipeline supports PP-OCRv3/v4/v5/v6, and optional document orientation/unwarping/textline orientation components can be disabled. Source: [General OCR pipeline usage](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md).
- PaddleOCR inference engines: current PaddleOCR supports `paddle`, `paddle_static`, `paddle_dynamic`, `transformers`, and `onnxruntime`, with PaddlePaddle remaining the default in most local inference cases. Source: [Inference Engine and Configuration](https://www.paddleocr.ai/main/en/version3.x/inference_deployment/local_inference/inference_engine.html).
- PaddlePaddle macOS install: macOS supports CPU-only PaddlePaddle, Apple Silicon arm64, and Python 3.9 through 3.13; the current macOS pip command installs `paddlepaddle==3.3.0` from the official stable CPU index. Source: [Install on macOS via PIP](https://www.paddlepaddle.org.cn/documentation/docs/en/install/pip/macos-pip_en.html).
- ONNX Runtime Python: use `pip install onnxruntime` for CPU and macOS/Arm-based CPUs; install only one ONNX Runtime package per environment. Official ONNX Runtime builds may enable telemetry, and the process-lifetime opt-out is `ORT_DISABLE_TELEMETRY=1` before initialization. Sources: [ONNX Runtime Python quickstart](https://onnxruntime.ai/docs/get-started/with-python.html) and [ONNX Runtime privacy notes](https://github.com/microsoft/onnxruntime/blob/main/docs/Privacy.md).
- PyAV: current PyAV requires Python 3.12+ and provides macOS binary wheels with FFmpeg bundled; frame objects expose `pts`, `time_base`, and `time`, where `time` is presentation time in seconds. Sources: [PyAV installation docs](https://github.com/PyAV-Org/PyAV/blob/main/docs/overview/installation.rst?plain=1) and [PyAV frame API](https://pyav.basswood.io/docs/18.1/api/frame.html).
- PyInstaller: current PyInstaller supports Python 3.8+ and creates macOS `.app` bundles with `--windowed`; onefile windowed app bundles are explicitly not recommended for signed/notarized sandboxed distribution. Source: [PyInstaller usage docs](https://www.pyinstaller.org/en/stable/usage.html).
- PySide6 / Qt for Python: PySide6 is the official Python binding for Qt and is available under LGPLv3/GPLv3/commercial licensing; Qt macOS apps are normally distributed as self-contained app bundles. Sources: [Qt for Python](https://doc.qt.io/qtforpython-6/) and [Qt for macOS](https://doc.qt.io/qtforpython-6/overviews/qtdoc-macos.html).
- GitHub Actions runners: public repositories have standard Apple Silicon macOS runner labels such as `macos-latest`, `macos-14`, `macos-15`, and `macos-26`; standard arm64 macOS runners are M1-class with 7 GB RAM. Source: [GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
- GitHub Pages Actions: current Pages workflows use `actions/configure-pages`, `actions/upload-pages-artifact`, and `actions/deploy-pages`. Source: [Deploying your website automatically](https://docs.github.com/en/get-started/start-your-journey/deploying-your-website-automatically).
- GitHub Releases: release assets expose `browser_download_url`, and public release assets can be downloaded without authentication. Sources: [Releases REST API](https://docs.github.com/en/rest/releases/releases) and [Release assets REST API](https://docs.github.com/en/rest/releases/assets).
- Apple distribution: Developer ID signing and notarization are recommended for apps distributed outside the Mac App Store; hardened runtime is required for notarization; Apple no longer accepts notarization uploads through `altool`. Sources: [Apple macOS distribution](https://developer.apple.com/macos/distribution/), [Distribute outside the Mac App Store](https://help.apple.com/xcode/mac/current/en.lproj/dev033e997ca.html), and [Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

## Architecture Decision

Use Python 3.13 on Apple Silicon, PySide6 for the GUI, PyAV for decoding, PaddleOCR with PaddlePaddle CPU as the default backend, and keep ONNX Runtime available as an alternate backend for packaging/performance comparison.

Reasons:

- PaddlePaddle has current official macOS Apple Silicon CPU support.
- PaddleOCR 3.7 provides PP-OCRv6 medium as the current default general OCR pipeline.
- PyAV exposes presentation timestamps directly and avoids OpenCV's more opaque video timestamp behavior.
- PyInstaller onedir/windowed is better aligned with signed macOS app distribution than onefile.
- PySide6 is mature enough for a normal Mac utility, provided LGPL obligations are preserved.

## Required Proofs Before Public v1.0.0

These are release gates. Do not claim release readiness until each item has a dated pass/fail result.

- [x] 2026-09-21: Install pinned dependencies in a fresh Python 3.13 arm64 virtual environment.
- [x] 2026-09-21: Load PaddleOCR with the PaddlePaddle backend in source and frozen app self-tests.
- [ ] Load PaddleOCR with ONNX Runtime or document why it is not viable. `onnxruntime` imports, but OCR inference with that backend has not been benchmarked.
- [x] 2026-09-21: OCR a synthetic 1920x1080 frame and capture text, confidence, and polygons.
- [x] 2026-09-21: OCR a synthetic 3840x2160 frame and measure small-text behavior.
- [x] 2026-09-21: Decode MOV/MP4 samples through PyAV and verify presentation timestamps.
- [x] 2026-09-21: Decode a generated ProRes MOV sample through PyAV and verify timestamps.
- [x] 2026-09-21: Build `Find That Text.app` through PyInstaller on Apple Silicon.
- [x] 2026-09-21: Launch the packaged binary without the development virtual environment via `--self-test-ocr`.
- [ ] Scan a controlled test video with the packaged GUI. Source CLI scans have passed; packaged GUI interaction has not been manually exercised.
- [ ] Build a DMG and verify install/open behavior on a clean Mac user account. A local DMG was created and checksum-verified on 2026-09-21, but clean-account install/open testing is still pending.
- [ ] Complete license audit for redistributed PyAV/FFmpeg, PaddleOCR models, PaddlePaddle, Qt/PySide6, and PyInstaller.
- [ ] Exercise signing/notarization workflow when Developer ID credentials are available.

## 2026-09-21 Validation Results

- Unit tests: `10 passed`.
- Default frame-step sampling: a 30 fps fixture scanned from `00:00:00` to `00:00:02` sampled source frames `0, 23, 46`.
- Advanced frame-step sampling: the same fixture scanned every frame from `00:00:00` to `00:00:01`, producing 31 inclusive samples.
- Source CLI range dry run: `find-that-text scan .spike/timestamp_fixture.mov --mode default --start 00:00:00 --end 00:00:02 --dry-run-empty-ocr` produced CSV, HTML, and raw JSON with `frame_step: 23`, `start_seconds: 0.0`, and `end_seconds: 2.0`.
- OCR technical spike: PaddleOCR found expected synthetic text on 1920x1080 and 3840x2160 frames.
- Packaged OCR self-test: `dist/Find That Text.app/Contents/MacOS/Find That Text --self-test-ocr` loaded the frozen PaddleOCR stack and recognized `HELLOWORLD`.
- Packaged artifacts: app bundle size was about 895 MB; DMG size was about 389 MB; bundled PP-OCRv6 model cache was about 133 MB.
- DMG checksum: `de787bb96e97d692bf18337fa0c8d641fd5ae0f9f05d3480e1c058efac5f47e5`.
- DMG verification: `hdiutil verify` reported the disk image checksum as valid.

## Known Constraints

- macOS GPU acceleration is not assumed. The official PaddlePaddle macOS path is CPU-only.
- The initial implementation is conservative about filtering. It stores all OCR detections in raw JSON and groups events only for the human report.
- Bundled model packaging has a local frozen-app proof, but the release still needs clean-account install/open testing before public distribution.
