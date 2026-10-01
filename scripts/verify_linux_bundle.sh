#!/usr/bin/env bash
set -euo pipefail

bundle="$(cd "$1" && pwd)"
executable="$bundle/Find That Text"
test -x "$executable"
test -f "$bundle/_internal/libmklml_intel.so"
for model in PP-OCRv6_small_det PP-OCRv6_small_rec; do
  test -d "$bundle/_internal/PaddleX/official_models/$model"
  test -n "$(ls -A "$bundle/_internal/PaddleX/official_models/$model")"
done

test_root="$(mktemp -d)"
trap 'status=$?; if ((status != 0)); then cat "$test_root/self-test.log" 2>/dev/null || true; fi; rm -rf "$test_root"' EXIT
mkdir -p "$test_root/home"
ffmpeg -hide_banner -loglevel error -f lavfi -i color=c=black:s=320x180:r=24 -frames:v 48 -c:v mpeg4 "$test_root/test.mp4"
printf '1\n00:00:00,000 --> 00:00:00,200\nSpeaking\n' > "$test_root/test.srt"

export FIND_THAT_TEXT_APP_SUPPORT="$test_root/app-support"
export FIND_THAT_TEXT_SELF_TEST_LOG="$test_root/self-test.log"
export HOME="$test_root/home"
unset PADDLE_PDX_CACHE_HOME PYTHONPATH PYTHONHOME LD_LIBRARY_PATH
export PATH=/usr/bin:/bin

for test_arg in --self-test --self-test-ocr; do
  printf 'Running packaged %s\n' "$test_arg"
  "$executable" "$test_arg"
done
printf 'Running packaged --self-test-gui\n'
qt_plugin="$(find "$bundle/_internal" -name libqxcb.so -print -quit)"
test -n "$qt_plugin"
ldd "$qt_plugin"
QT_DEBUG_PLUGINS=1 xvfb-run -a "$executable" --self-test-gui
printf 'Running packaged --self-test-scan\n'
"$executable" --self-test-scan "$test_root/test.mp4"

for model in PP-OCRv6_small_det PP-OCRv6_small_rec; do
  test -d "$test_root/app-support/PaddleX/official_models/$model"
done
printf 'Extracted Linux bundle passed import, GUI, OCR, and report checks\n'
