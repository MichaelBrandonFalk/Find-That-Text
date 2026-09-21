#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION="$(tr -d '\n' < VERSION)"
APP_PATH="dist/Find That Text.app"
DMG_PATH="dist/Find-That-Text-v${VERSION}-macOS-Apple-Silicon.dmg"
SHA_PATH="dist/Find-That-Text-v${VERSION}-SHA256.txt"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing $APP_PATH. Run scripts/build_macos.sh first." >&2
  exit 1
fi

rm -f "$DMG_PATH" "$SHA_PATH"
hdiutil create \
  -volname "Find That Text ${VERSION}" \
  -srcfolder "$APP_PATH" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

shasum -a 256 "$DMG_PATH" > "$SHA_PATH"
echo "Created $DMG_PATH"
echo "Created $SHA_PATH"
