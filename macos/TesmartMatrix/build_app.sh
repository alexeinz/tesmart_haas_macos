#!/bin/bash
# Builds dist/TesmartMatrix.app (release, ad-hoc signed) and optionally opens it.
set -euo pipefail
cd "$(dirname "$0")"

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
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundleVersion</key><string>1</string>
    <key>LSMinimumSystemVersion</key><string>13.0</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSLocalNetworkUsageDescription</key><string>Controls the TESmart HDMI matrix on your local network.</string>
</dict>
</plist>
PLIST

codesign --force --sign - "$APP"
echo "Built $APP"
[ "${1:-}" = "--open" ] && open "$APP"
true
