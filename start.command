#!/bin/zsh
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  echo "请先按 README 创建 Python 3.11 虚拟环境并安装依赖。"
  read -k 1
  exit 1
fi
exec .venv/bin/python launch.py
