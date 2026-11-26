#!/bin/bash
# 安装：复制到 ~/.agy-cn，并在 ~/Applications 生成「Antigravity 中文.app」。不需要 sudo，不联网。
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.agy-cn"
APP="$HOME/Applications/Antigravity 中文.app"
LOG="$HOME/Library/Logs/agy-cn.log"
PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "[错误] 未找到 python3，请先安装 Xcode Command Line Tools (xcode-select --install) 或 Homebrew Python。" >&2
  exit 1
fi
mkdir -p "$DEST" "$HOME/Applications" "$HOME/Library/Logs"
cp "$SRC/launcher.py" "$SRC/overlay.js" "$SRC/zh-CN.json" "$DEST/"
"$PY" -c "import json;json.load(open('$DEST/zh-CN.json'))"
rm -rf "$APP"
osacompile -o "$APP" -e "do shell script \"nohup '$PY' '$DEST/launcher.py' >>'$LOG' 2>&1 &\""
ICON="/Applications/Antigravity.app/Contents/Resources/$(defaults read /Applications/Antigravity.app/Contents/Info CFBundleIconFile 2>/dev/null | sed 's/\.icns$//').icns"
[ -f "$ICON" ] && cp "$ICON" "$APP/Contents/Resources/applet.icns" || true
touch "$APP"
echo "安装完成：$APP (Python: $PY)"
echo "使用：先 ⌘Q 退出 Antigravity，再打开「Antigravity 中文」。"
