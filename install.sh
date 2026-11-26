#!/bin/bash
# 安装：复制到 ~/.agy-cn，并在 ~/Applications 生成「Antigravity 中文.app」。不需要 sudo，不联网。
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.agy-cn"
APP="$HOME/Applications/Antigravity 中文.app"
mkdir -p "$DEST" "$HOME/Applications"
cp "$SRC/launcher.py" "$SRC/overlay.js" "$SRC/zh-CN.json" "$DEST/"
python3 -c "import json;json.load(open('$DEST/zh-CN.json'))"
rm -rf "$APP"
osacompile -o "$APP" -e "do shell script \"nohup /usr/bin/python3 '$DEST/launcher.py' >/dev/null 2>&1 &\""
ICON="/Applications/Antigravity.app/Contents/Resources/$(defaults read /Applications/Antigravity.app/Contents/Info CFBundleIconFile 2>/dev/null | sed 's/\.icns$//').icns"
[ -f "$ICON" ] && cp "$ICON" "$APP/Contents/Resources/applet.icns" || true
touch "$APP"
echo "安装完成：$APP"
echo "使用：先 ⌘Q 退出 Antigravity，再打开「Antigravity 中文」。"
