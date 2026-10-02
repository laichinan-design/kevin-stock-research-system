# Kevin 投資研究系統 — Claude 工作規範

使用者：Kevin（台中，台股/半導體供應鏈投資研究者）。一律繁體中文，技術詞（EPS、capex、P/E、CAGR、CPO…）保留英文。結論先行、表格優先、幣別標 NT$。

## 個股研究：kevin-stock-research plugin（主流程）

本 repo 內建 plugin `plugins/kevin-stock-research/`（0.3.0），經 `.claude/settings.json` 以專案 marketplace `kevin-research-bundle` 自動啟用，雲端與本機 session 都會載入。

| 使用者要求 | 由誰處理 |
|---|---|
| 「完整研究 TWSE:XXXX」「建立研究資料夾」「研究更新」「多股比較」「盤後追蹤」「部位規劃」 | plugin 的 `research-router`（再分派 data-acquisition → document-organizer → fundamental-research → kevin-model → report-validation） |
| 「Kevin股價模型」對話內快速估值、加同業 | 帳戶 skill `kevin-stock-pricing-model` |
| 「台股雙法」 | 帳戶 skill `tw-ai-dual-valuation` |
| 「更新投資組合」整本 workbook | 帳戶 skill `update-portfolio` |
| 產業鏈、競爭、DCF、空方紅隊補充分析 | 帳戶 skill `invest-industry-map`／`invest-competitor-analysis`／`invest-dcf-valuation`／`invest-bear-case`（plugin 沒有 DCF 計算器） |

- 研究資料夾放在 `研究資料/<market>-<ticker>/`（例 `研究資料/TWSE-2330/`），每股獨立，不混放。
- plugin 指令細節見 `plugins/kevin-stock-research/references/cli.md`；能力邊界見 `references/capabilities.md`，未實作的不得宣稱已執行。
- 依賴：`pip install -r plugins/kevin-stock-research/requirements.txt`（openpyxl、pypdfium2）。
- 修改 plugin：先改 `plugins/kevin-stock-research/`、更新版本與 CHANGELOG、跑 `python3 -m unittest discover -s plugins/kevin-stock-research/scripts -p "test_*.py"`；正式來源仍是 Google Drive「投資組合-台股/Kevin 股票分析Plugin」的 release，兩邊版本需一致。

## Kevin 模型口徑（2026-10 版，所有流程一致）

1. **基準 PE 雙層錨定**：base = ETF PE × ratio × M_adj（投資組合 0050 0.75/0.55、CPO 00891 0.85/0.62、潛力股 00935 0.85/0.62）。舊版固定 15/10、25/20、30/25 已停用。錨定值標日期，超過 45 天提醒。
2. **H 用合併淨利率**（本期淨利 ÷ 營收），**W = 歸母淨利 ÷ 合併淨利**。不可用歸母淨利率再乘 W（重複扣除）。
3. **G/H 只取最新一期已公告財報**原始數字自己算；禁止法人預估、媒體推估、外推、上期沿用。
4. **盈餘品質**：非經常性占稅前 ≥ 10% 時帳面與本業兩版並列，由使用者選。
5. **股本 I** 取官方實收資本額，嚴禁以淨利 ÷ EPS 反推。
6. **E** 為 1–n 月累計（千元），年化因子 12/n。
7. **溢價只乘目標價**，不進 EPS。負成長時 P、Q 用 base，標示不適用。
8. 散熱 / CPO / 先進封裝設備加註線性年化可能低估 H2 ramp，並列情境 B。
9. 抓不到的數字標 N/A，不憑記憶填補；有假設就明講。

## 免責

報告與對話結尾附一次「非投資建議」，不重複警示。

## 其他專案

- `三電系統開發/`：達方 E-mobility 三電系統 BOM 與訂閱制研究（非個股流程）。
