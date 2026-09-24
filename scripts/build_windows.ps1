$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

python -m pip install -r requirements-windows-x64.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m pip install -e . --no-deps
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/release_check.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:PADDLE_PDX_CACHE_HOME = Join-Path $root ".paddlex-cache"
$env:PADDLE_PDX_MODEL_SOURCE = "bos"
python -c "from find_that_text.ocr.engine import PaddleOCREngine; PaddleOCREngine()"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m PyInstaller --clean --noconfirm packaging/FindThatTextWindows.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$version = (Get-Content VERSION -Raw).Trim()
$archive = Join-Path $root "dist/Find-That-Text-v$version-Windows-x64.zip"
Compress-Archive -Path (Join-Path $root "dist/Find That Text") -DestinationPath $archive -Force
Write-Output "Built $archive"
