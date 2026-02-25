#!/bin/bash
# setup.sh

# 가상 환경 생성
python3 -m venv venv

# 가상 환경 활성화 및 fonttools 설치
source venv/bin/activate
pip install --upgrade pip
pip install fonttools
pip install PySide6

echo "------------------------------------------------"
echo "Setup complete!"
echo "To use the script, run: source venv/bin/activate"
echo "------------------------------------------------"
