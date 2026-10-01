#!/usr/bin/env bash
# 一鍵執行：計算 → Excel → Word。用法：bash run_pipeline.sh 個股研究/研究/<代號_名稱>/<YYYYMMDD>/research.json
set -euo pipefail
JSON="$1"
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 -c "import openpyxl, docx" 2>/dev/null || pip install -q openpyxl python-docx
python3 "$DIR/kevin_engine.py" "$JSON" --print
python3 "$DIR/build_excel.py" "$JSON"
python3 "$DIR/build_report.py" "$JSON"
