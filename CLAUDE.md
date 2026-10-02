# Kevin 投資研究系統 — Claude 工作規範

使用者：Kevin（台中，台股/半導體供應鏈投資研究者）。一律繁體中文，技術詞（EPS、capex、P/E、CAGR、CPO…）保留英文。結論先行、表格優先、幣別標 NT$。

## 個股研究：kevin-stock-research plugin（主流程）

本 repo 內建 plugin `plugins/kevin-stock-research/`（0.7.0），經 `.claude/settings.json` 以專案 marketplace `kevin-research-bundle` 自動啟用，雲端與本機 session 都會載入。

| 使用者要求 | 由誰處理 |
|---|---|
| 「完整研究 TWSE:XXXX」「建立研究資料夾」「研究更新」「多股比較」「盤後追蹤」「部位規劃」 | plugin 的 `research-router`（再分派 data-acquisition → document-organizer → fundamental-research → engineering-visuals → kevin-model → integrated-deck → report-validation） |
| 「Kevin股價模型」對話內快速估值、加同業 | 帳戶 skill `kevin-stock-pricing-model` |
| 「台股雙法」 | 帳戶 skill `tw-ai-dual-valuation` |
| 「更新投資組合」整本 workbook | 帳戶 skill `update-portfolio` |
| 產業鏈、競爭、DCF、空方紅隊補充分析 | 帳戶 skill `invest-industry-map`／`invest-competitor-analysis`／`invest-dcf-valuation`／`invest-bear-case`（plugin 沒有 DCF 計算器） |

- 研究資料夾放在 `研究資料/<market>-<ticker>/`（例 `研究資料/TWSE-2330/`），每股獨立，不混放。
- plugin 指令細節見 `plugins/kevin-stock-research/references/cli.md`；能力邊界見 `references/capabilities.md`，未實作的不得宣稱已執行。
- 依賴：`pip install -r plugins/kevin-stock-research/requirements.txt`（openpyxl、pypdfium2；工程圖解與簡報另需 fonttools、brotli、cairosvg、python-pptx、Pillow）。
- 修改 plugin：先改 `plugins/kevin-stock-research/`、更新版本與 CHANGELOG、跑 `python3 -m unittest discover -s plugins/kevin-stock-research/scripts -p "test_*.py"`；正式來源仍是 Google Drive「投資組合-台股/Kevin 股票分析Plugin」的 release，兩邊版本需一致：`python3 tools/build_release.py` 產生 `dist/plugin-release-<版本>/`（package、內層 .plugin、總 ZIP、驗收紀錄），整個資料夾放到 Drive。安裝說明與 Codex catalog 在 `release/`。

## 研究結果存放位置（Google Drive）

個股研究、資料複核、估值等產出，一律存到 Google Drive，不要只放在對話或本 repo。

- 根目錄：`投資組合-台股`（folder id `1pTeqf8ZPtidGCKkHbgk67QGqQ97xx6Kg`）
- 個股子資料夾命名：`{公司簡稱}{代碼}`，不留空白，例如 `智邦2345`、`松川精密7788`、`新盛力4931`
- plugin 完整研究的輸出放在個股資料夾下的 `{公司簡稱}{代碼}研究/`（storage.drive_folder），分類PDF、工程圖解、整合簡報等子資料夾比照《竹陞6739研究》
  - 有少數既有資料夾的命名不同（例如 `AES-KY 6781`），沿用既有資料夾，不要重建
- 適用範圍：最新一份 `投資組合-台股/投資組合_YYYY_MM_DD_updated.xlsx` 裡「投資組合」「CPO概念」「潛力股」三張表列出的股票
  - 先搜尋 `parentId = '1pTeqf8ZPtidGCKkHbgk67QGqQ97xx6Kg'` 找既有的個股資料夾；沒有才建立
  - 不在清單內的股票：先問 Kevin 要存哪裡
- 檔名：`{代碼}_{公司簡稱}_{主題}_{YYYYMMDD}.xlsx`（或 `.docx`），例如 `2345_智邦_官方資料複核_20261001.xlsx`
- 上傳時保留原始格式（`disableConversionToGoogleType: true`），不要轉成 Google 格式

### 已知資料夾 ID

| 股票 | 資料夾 | ID |
|---|---|---|
| 智邦 2345 | `投資組合-台股/智邦2345` | `1DsnUljDO0kaNToZAVOjCAWu8SJYvz-GQ` |
| 智邦 2345 研究資料夾 | `投資組合-台股/智邦2345/智邦2345研究` | `1ejj72dCsUwto2Pw_CS1AKW1-ZsPbQKLD` |
| 矽格 6257 | `投資組合-台股/矽格6257` | `12pKaZ0oqRd02x9sksEc1zxXUG6ecjSCW` |
| 矽格 6257 研究資料夾 | `投資組合-台股/矽格6257/矽格6257研究` | `1MA01iKzAtfojAHFhZplxyomkFWJL0yrp` |
| 京元電 2449 | `投資組合-台股/京元電2449` | `1cpG5L85m8XF2LIfTw8IVrGPEYMknfRT1` |
| 京元電 2449 研究資料夾 | `投資組合-台股/京元電2449/京元電2449研究` | `1zIWMtb6hwSl4s7I4pj5aeSqhIBI3njrI` |

### 官方資料來源

- 雲端環境的網路政策會擋掉 MOPS／TWSE 網域（`mops.twse.com.tw`、`mopsov.twse.com.tw`、`openapi.twse.com.tw`、`www.twse.com.tw`）
- 個股資料夾通常已經放有 MOPS 下載的財報 PDF（`YYYYQQ_代碼_AI1_*.pdf` 是合併財報），請優先讀這份做官方複核
- 業主淨利占比用「歸母淨利 ÷ 本期淨利（合併）」計算；非控制權益為負數時，占比會大於 100%

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
