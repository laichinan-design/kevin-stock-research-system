# 個股研究流程

Kevin 台股個股研究的標準化流程：**Kevin 股價模型 → 台股雙法估值 → 產業鏈 → 競爭 → DCF → Bear case → 綜合結論**，所有數字集中在一份 `research.json`，由引擎計算後產出 Excel 模型與 Word 報告。完整規則見根目錄 `CLAUDE.md`。

## 使用方式

在 Claude Code 對話輸入：`個股研究 3017`（可多檔：`個股研究 3017 3324 3653`）。

手動執行：
```bash
python3 個股研究/tools/new_research.py 3017                 # 開案，帶入 watchlist 的 category/主題/W
# 填寫 個股研究/研究/3017_奇鋐/<YYYYMMDD>/research.json
bash 個股研究/tools/run_pipeline.sh 個股研究/研究/3017_奇鋐/<YYYYMMDD>/research.json
```

## 目錄

| 路徑 | 內容 |
|---|---|
| `tools/kevin_engine.py` | 計算引擎：Kevin 模型、雙法（含 ⚫ earnings explosion／資料矛盾偵測）、DCF 三情境＋5×5 敏感度；`--selftest` 以 SKILL.md 宜鼎範例驗算 |
| `tools/build_excel.py` | 連動 Excel：輸入／Kevin模型（含 H×E 淨利率敏感度）／雙法估值／DCF／定性評分，藍字可改 |
| `tools/build_report.py` | Word 報告：結論先行 → 八章 → 來源 → 免責 |
| `tools/new_research.py` | 開案腳本 |
| `tools/run_pipeline.sh` | 一鍵：計算 → Excel → Word |
| `templates/research_template.json` | 研究資料結構（每欄附來源欄位） |
| `config/watchlist.json` | AI 供應鏈觀察清單（category、主題、H2 ramp 旗標、已知 W） |
| `研究/<代號_名稱>/<YYYYMMDD>/` | 每次研究的 research.json、valuation.md、.xlsx、.docx |
| `研究索引.md` | 歷次研究結論一覽 |

## 模型公式摘要

| 項目 | 公式 |
|---|---|
| 預期 EPS N | E × H × W × (12/n) × 10 ÷ (I × 100000) × multiplier |
| 成長率 O | (N − J) / J |
| PE P / Q | 基礎 PE + (O×100)^(1/2) / (O×100)^(2/3)；投資組合 15/10、CPO 25/20、潛力股 30/25 |
| 目標價 T | (N×P + N×Q) / 2 |
| PEG | (M/N) ÷ (O×100)；<1 🟢、1–1.5 🟡、>1.5 🔴 |
| PE band | Low = Q×0.8、Mid = (P+Q)/2、High = P×1.2 |
| ⚫ 不適用 | O > 300%、M/N > 150、N ≤ 0、最新季 EPS > N |
| DCF | 10 年兩階段 FCF + Gordon 終值；Bull/Base/Bear = 20/60/20 機率加權 |

非投資建議。
