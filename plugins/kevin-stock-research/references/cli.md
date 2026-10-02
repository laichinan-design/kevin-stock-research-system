# 可執行指令

Python 3.11+。先在宿主找到可用Python；需要依賴時在獨立venv安裝requirements.txt。以下在plugin根目錄執行；路徑含空格時加引號。ROOT是使用者資料夾，不能是plugin目錄。

```text
python scripts/workflow.py --root ROOT init --market TWSE --ticker 2330 --name 台積電 --industry semiconductor
python scripts/workflow.py --root ROOT verify-identity --source OFFICIAL_HTTPS_URL --date YYYY-MM-DD
python scripts/workflow.py --root ROOT plan --mode full --asof YYYY-MM-DD
python scripts/workflow.py --root ROOT dedupe-check --manifest wanted.json [--known drive-listing.json]
python scripts/workflow.py --root ROOT ingest --manifest sources.json [--known drive-listing.json] [--force]
python scripts/workflow.py --root ROOT classify-pdfs [--manifest classify.json]
python scripts/workflow.py --root ROOT classify-pdfs [--manifest classify.json] --apply
python scripts/workflow.py --root ROOT extract --evidence-id SOURCE_ID
python scripts/workflow.py --root ROOT facts --file facts.json --asof YYYY-MM-DD
python scripts/workflow.py --root ROOT audit-model original.xlsx
python scripts/workflow.py --root ROOT update-model --original original.xlsx --destination new-copy.xlsx --mapping mapping.json --changes changes.json
python scripts/workflow.py --root ROOT value --request valuation.json
python scripts/workflow.py --root ROOT daily --date YYYY-MM-DD --calendar calendar.json
python scripts/workflow.py --root ROOT import-market --file market.json --asof YYYY-MM-DD
python scripts/workflow.py --root ROOT monitor --file state-input.json --date YYYY-MM-DD --slot manual
python scripts/workflow.py --root ROOT pending
python scripts/workflow.py --root ROOT ack ALERT_ID
python scripts/workflow.py --root ROOT batch-size --file portfolio-batch.json
python scripts/workflow.py --root ROOT compare --files facts-a.json facts-b.json --metric revenue
python scripts/workflow.py --root ROOT fill --record confirmed-fill.json
python scripts/workflow.py --root ROOT export
python scripts/workflow.py --root ROOT capabilities
python scripts/workflow.py --root OLD_ROOT migrate
python scripts/workflow.py --root OLD_ROOT migrate --apply
python -B -m unittest discover -s scripts -p "test_*.py" -v
```

init只驗格式；verify-identity只保存已完成查核的聲明。根目錄與名稱不是自動官方驗證。model/profile、calendar與facts的verified只能在實際查核後填true。
plan產生待執行步驟和resolved_config；不是一鍵抓完資料或完成研究。宿主依技能完成讀取、判讀與Word／Excel交付。

## sources.json
JSON陣列。每筆security/category/url/title/published/fiscal_period/suffix；本機檔附local_path。local_path仍保留真實來源URL。metadata/blocked可不含bytes，status不能假填full。

## 下載前去重（dedupe-check／ingest）
wanted.json：陣列，元素可為檔名字串，或含 url／original_filename／sha256 的物件（MOPS 網址自動取 filename 參數）。回傳 download 與 skip（含原因）。
比對順序：SHA256 → 同檔名（研究庫、分類PDF、PDF分類索引、--known 清單）→ 文件鍵（01年報／02年度合併財報／03合併季報 的 期別＋語言）。例：已有 竹陞_6739_2025_年報_中文.pdf 時，2025_6739_20260527F04.pdf 會被略過；FE4（英文）不算重複。
--known：JSON陣列或 {"files":[...]}，每筆可有 title／filename／original_filename／sha256；可直接存 Drive 搜尋結果。
ingest 對遠端來源套用同一檢查，略過者列在 skipped_already_held；--force 才重抓。本機 local_path 與 metadata／blocked 不受影響。mops.pending(rows, known) 供 discover 結果在下載前分流。

## PDF 分類（classify-pdfs）
輸入：證據庫 status=full 的 PDF、分類PDF 內既有 PDF、上一版 PDF分類索引.json，以及選用的 classify.json。
classify.json：陣列。新增本機檔用 {"local_path":...,"url":...}；指定或更正分類用 sha256／evidence_id／original_filename 擇一比對（須唯一），欄位 category、label、title、language（中文／英文）、publisher、note、classification_basis。
預設 dry-run 不寫檔；--apply 建立硬連結（跨磁碟才複製，storage=copy）、空類別放 目前無檔案.txt，並輸出 PDF分類索引.json／.xlsx、PDF分類目錄.html、整理說明.md。
既有分類檔不改名不搬移；計算類別與所在資料夾不同時列 conflicts。MOPS 檔名屬其他代碼、無法判定類別、規則不符者列 unclassified。index 欄位與健策 3653 版相容（files[]、label、date_meaning、source_urls、storage）。

## 模型 changes.json
JSON陣列，每筆例如：
```json
{"sheet":"Portfolio","cell":"D2","value":100,"security":"TWSE:2330","source_id":"ACTUAL_EVIDENCE_ID","asof":"2026-09-30","basis":"TWD"}
```
這是合成格式示例，不是實際股價。basis須與mapping.inputs中的unit完全一致。每次原工作簿變更需重核mapping雜湊；formula_cells不能用一般輸入更新。原始公式另由已核對的recalculate及獨立算術驗證。

## Kevin 估值請求（value，method=kevin_legacy）
完整欄位見examples/kevin-valuation.template.json與references/kevin-model.md。以下為合成格式示例，不是實際財報或股價：
```json
{"security":"TWSE:2330","industry":"semiconductor","method":"kevin_legacy","currency":"TWD","asof":"2026-09-30","assumptions_asof":"2026-09-30","assumptions_verified":true,"source_ids":["ACTUAL_EVIDENCE_ID"],
 "inputs":{"revenue_ytd":800,"months":8,"owner_ratio":1,"capital_thousands":100,"par":10,"previous_eps":20,
  "earnings_quality":{"scope":"consolidated","revenue":600,"pretax":200,"tax":40,"net_income":160,"nonrecurring":{"fvtpl":0,"disposals":0,"fx":5}},
  "anchor":{"category":"potential","etf_pe":30,"market_pe":25,"market_median_pe":17,"asof":"2026-09-30"}}}
```
回傳scenarios.A（主要）、選用的scenarios.B、earnings_quality、anchor、warnings、flags。溢價用target_premium，只乘模型價；0.2.0的multiplier（≠1）與base_pe_low／base_pe_high會被拒絕並提示新欄位。

## portfolio-batch.json
account：account_id、snapshot_id、asof、currency、investable_assets、available_cash、loss_budget_remaining、sector_values（sector→市值）。
requests為優先序陣列；每筆security/currency/sector/personal/signal。personal包含holding_shares、average_cost、single_stock_limit、sector_limit、risk_per_share、core_ratio、tactical_ratio、batch_budget、fee_rate、minimum_fee、sell_fee_rate、sell_tax_rate；比例0–1、核心＋機動=1。signal包含model_verified、data_current、thesis_valid、price、buy_max。缺必要個人資料只產生conditional_only。預算與sector_values需同一帳戶及同一估值截止日。
batch-size不預留現金、不更動持股；同一snapshot_id的不同方案不能同時執行。單股也使用requests只有一筆的batch。

## state-input.json
至少包含security；可有decision、risk_state、zone、valuation、source_failures（字串陣列）、announcements（穩定事件ID陣列）。由已核對來源產生，valuation同一模型同一幣別才比較。monitor-state.json是SQLite權威狀態的可讀鏡像，勿手改。舊monitor state含義不明時另用新檔，保留舊檔；不得從其他股票複製。

## 遷移
migrate預設dry-run；--apply只備份並轉config，不移動／刪除證據，不改任何宿主既有排程。新配置需重核身分、產業、幣別、會計年度、模型與行事曆。請先查看原宿主排程再切換，不同平台勿同時維護同一root。

## 驗收資料
全部自動測試用合成資料及暫存檔；測試公司／價格不是研究數據。原21項測試保留行為回歸，模型更新案例調整為新強制映射介面；新增跨股／口徑／股數／日曆測試。套件tests通過不代表網路資料或兩平台實際安裝已驗收。
