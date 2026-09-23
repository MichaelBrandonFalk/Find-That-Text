# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import importlib.util

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

project_root = Path(SPECPATH).parent
version = (project_root / "VERSION").read_text(encoding="utf-8").strip()
datas = [
    (str(project_root / "VERSION"), "."),
    (str(project_root / "PRIVACY.md"), "."),
    (str(project_root / "THIRD_PARTY_NOTICES.md"), "."),
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
if model_cache.exists():
    for model_name in ["PP-OCRv6_small_det", "PP-OCRv6_small_rec"]:
        model_dir = model_cache / model_name
        if model_dir.exists():
            datas.append((str(model_dir), f"PaddleX/official_models/{model_name}"))

a = Analysis(
    [str(project_root / "src" / "find_that_text" / "app.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
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
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
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
app = BUNDLE(
    coll,
    name="Find That Text.app",
    icon=None,
    bundle_identifier="org.findthattext.app",
    info_plist={
        "CFBundleDisplayName": "Find That Text",
        "CFBundleName": "Find That Text",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "NSHighResolutionCapable": True,
    },
)
