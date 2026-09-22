# OCR Evaluation For The Next Release

The shipping scanner uses PaddleOCR 3.7.0 with separate PP-OCRv6 small detection and recognition models. Frame sampling, caption-gap filtering, scene selection, and OCR are independent stages. A detector and recognizer can be mixed, or a second engine can inspect only uncertain crops, but each added stage has a speed, bundle-size, and maintenance cost.

## What The Sources Show

- [PaddleOCR's PP-OCRv6 results](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv6/PP-OCRv6.en.md) give the small model a stronger Screen and Card recognition result than tiny on its own data. Its Apple M4 end-to-end table reports 3.07 seconds per image for small with PaddlePaddle and 1.29 seconds with ONNX Runtime. Those images and settings are not our film workload.
- [PaddleOCR's module APIs](https://www.paddleocr.ai/main/en/version3.x/module_usage/text_detection.html) expose detection and recognition separately and support ONNX Runtime. This makes a same-model runtime comparison the least disruptive first experiment.
- [RapidOCR](https://github.com/RapidAI/RapidOCR) packages OCR models, including Paddle-derived models, with alternate runtimes. It is not automatically a different recognition model. Its [M2 CoreML comparison](https://rapidai.github.io/RapidOCRDocs/main/en/blog/2026/02/28/coreml-vs-cpu-provider-onnxruntime-rapidocr/) found the tested CoreML provider slower than CPU, so Apple acceleration needs measurement rather than assumption.
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) is a genuine alternate detector/recognizer stack based on CRAFT and PyTorch. [Tesseract](https://github.com/tesseract-ocr/tesseract) is a useful lightweight baseline, particularly with sparse-text segmentation, but neither project's general claims establish forced-text recall on films.

## Decision Test

1. Assemble 80 to 120 labeled frames or short excerpts covering opening titles, phone screens, signs, letters, lower thirds, credits, dark scenes, and decorative false positives. Include examples with and without text and a few frames just before and after each change.
2. On the same Apple Silicon Mac, compare current PaddleOCR small, the same small models under ONNX Runtime, PP-OCRv6 tiny, EasyOCR, and Tesseract. Keep image scaling and frame selection fixed.
3. Measure whether each important text moment was found, false-positive review burden, transcription quality, median and 95th-percentile warm inference time, startup time, memory use, and packaged app size.
4. Keep the existing engine unless another option improves the speed and review experience without losing important moments. A final end-to-end feature scan is still needed to validate the two-hour goal, but not to choose candidates for that scan.
