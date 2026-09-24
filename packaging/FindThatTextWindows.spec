# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import importlib.util

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

project_root = Path(SPECPATH).parent
datas = [
    (str(project_root / "VERSION"), "."),
    (str(project_root / "PRIVACY.md"), "."),
    (str(project_root / "THIRD_PARTY_NOTICES.md"), "."),
    (str(project_root / "src" / "find_that_text" / "resources" / "app-icon.png"), "find_that_text/resources"),
]
for package_name in [
    "imagesize",
    "opencv-contrib-python",
    "opencv-python",
    "pyclipper",
    "pypdfium2",
    "python-bidi",
    "shapely",
    "scenedetect",
    "wordfreq",
]:
    datas += copy_metadata(package_name)
datas += collect_data_files(
    "wordfreq",
    includes=["data/small_en.msgpack.gz", "data/small_es.msgpack.gz"],
)
paddlex_spec = importlib.util.find_spec("paddlex")
if paddlex_spec and paddlex_spec.submodule_search_locations:
    paddlex_root = Path(paddlex_spec.submodule_search_locations[0])
    ocr_pipeline_config = paddlex_root / "configs" / "pipelines" / "OCR.yaml"
    if ocr_pipeline_config.exists():
        datas.append((str(ocr_pipeline_config), "PaddleX/configs/pipelines"))
model_cache = project_root / ".paddlex-cache" / "official_models"
for model_name in ["PP-OCRv6_small_det", "PP-OCRv6_small_rec"]:
    model_dir = model_cache / model_name
    if not model_dir.exists():
        raise FileNotFoundError(f"Required bundled OCR model missing: {model_dir}")
    datas.append((str(model_dir), f"PaddleX/official_models/{model_name}"))

a = Analysis(
    [str(project_root / "src" / "find_that_text" / "app.py")],
    pathex=[str(project_root / "src")],
    binaries=collect_dynamic_libs("paddle"),
    datas=datas,
    hiddenimports=[
        "paddle",
        "paddleocr",
        "scenedetect",
        "scenedetect.detectors",
        "av",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Find That Text",
    icon=str(project_root / "packaging" / "FindThatText.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Find That Text",
)
