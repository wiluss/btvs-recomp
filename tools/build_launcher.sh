#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
app='build/btvs-recomp.app'
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
xcrun swiftc -module-cache-path "$PWD/build/launcher-module-cache" -O -parse-as-library -target arm64-apple-macosx13.0 \
    src/launcher/*.swift \
    -o "$app/Contents/MacOS/BuffyLauncher"
xcrun swift -module-cache-path "$PWD/build/launcher-module-cache" tools/launcher_icon.swift "$PWD/build/Launcher.iconset"
iconutil -c icns build/Launcher.iconset -o "$app/Contents/Resources/Launcher.icns"
cp src/launcher/Localizations.json "$app/Contents/Resources/Localizations.json"
cp docs/branding/logo.png "$app/Contents/Resources/Logo.png"
cp docs/branding/moon.png "$app/Contents/Resources/LogoMoon.png"
cat > "$app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key><string>BuffyLauncher</string>
    <key>CFBundleIdentifier</key><string>local.buffy.macos.launcher</string>
    <key>CFBundleName</key><string>btvs-recomp</string>
    <key>CFBundleDisplayName</key><string>btvs-recomp</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleIconFile</key><string>Launcher</string>
    <key>CFBundleVersion</key><string>1</string>
    <key>LSMinimumSystemVersion</key><string>13.0</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST
version=$(cat VERSION)
marketing=${version%%-*}
plutil -insert CFBundleShortVersionString -string "$marketing" "$app/Contents/Info.plist"
plutil -insert CFBundleGetInfoString -string "btvs-recomp $version" "$app/Contents/Info.plist"
codesign --force --sign - "$app"
printf '%s\n' "$PWD/$app"
