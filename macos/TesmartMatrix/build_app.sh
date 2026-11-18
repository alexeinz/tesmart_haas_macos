#!/bin/bash
# Builds dist/TesmartMatrix.app (release, ad-hoc signed) and optionally opens it.
set -euo pipefail
cd "$(dirname "$0")"
VERSION="${VERSION:-1.0}"

swift build -c release
BIN="$(swift build -c release --show-bin-path)/TesmartMatrix"

APP="dist/TesmartMatrix.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/TesmartMatrix"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>TESmart Matrix</string>
    <key>CFBundleDisplayName</key><string>TESmart Matrix</string>
    <key>CFBundleIdentifier</key><string>local.tesmart.matrix</string>
    <key>CFBundleExecutable</key><string>TesmartMatrix</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>__VERSION__</string>
    <key>CFBundleVersion</key><string>__VERSION__</string>
    <key>LSMinimumSystemVersion</key><string>13.0</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSLocalNetworkUsageDescription</key><string>Controls the TESmart HDMI matrix on your local network.</string>
</dict>
</plist>
PLIST

sed -i.bak "s/__VERSION__/$VERSION/g" "$APP/Contents/Info.plist" && rm "$APP/Contents/Info.plist.bak"
codesign --force --sign - "$APP"
echo "Built $APP"
[ "${1:-}" = "--open" ] && open "$APP"
true
