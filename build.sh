#!/usr/bin/env bash
# 一键打包为单个 exe：VSUnityInstaller.exe
set -e
cd "$(dirname "$0")"

python -m PyInstaller --clean --noconfirm \
  --onefile --windowed --name VSUnityInstaller \
  main.py

echo
echo "完成。输出: dist/VSUnityInstaller.exe"