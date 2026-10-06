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
python scripts/workflow.py --root ROOT set-industry --industry semiconductor-equipment
python scripts/workflow.py --root ROOT set-industry --industry datacenter-networking
python scripts/workflow.py --root ROOT set-industry --industry osat
python scripts/workflow.py --root ROOT set-storage [--drive-folder "投資組合-台股/{short}{ticker}/{short}{ticker}研究"] [--local-sync-root "G:/我的雲端硬碟"] [--connector-max-bytes 100000]
python scripts/workflow.py --root ROOT drive-sync [--apply]
python scripts/workflow.py --root ROOT drive-record --path 正式成果/報告.docx [--file-id DRIVE_ID] [--via manual]
python scripts/workflow.py --root ROOT gaps --asof YYYY-MM-DD [--years 2]
python scripts/workflow.py --root ROOT coverage-set --doc "2025 年報" --pages 1-76 --total 101 --missing 77-101 --note "…"
python scripts/workflow.py --root ROOT readme
python scripts/workflow.py --root ROOT set-deck-style --palette 07 --font C [--cjk-font "Noto Sans TC"]
python scripts/workflow.py --root ROOT visual-build --spec 01.json 02.json [--font-dir DIR]
python scripts/workflow.py --root ROOT visual-outline [--file old.svg ...] [--font-dir DIR]
python scripts/workflow.py --root ROOT visual-check [--file x.svg ...]
python scripts/workflow.py --root ROOT deck-build --spec deck.json --pdf
python scripts/workflow.py --root ROOT deck-check --file deck.pptx
python scripts/workflow.py --root ROOT deck-fonts --file deck.pptx
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

## 產業模組（set-industry）
十種：general、growth-manufacturing、semiconductor、semiconductor-equipment（設備與廠務自動化）、datacenter-networking（資料中心網通與交換器 ODM／JDM）、osat（半導體封裝測試）、cyclical、financial、asset-based、loss-making。set-industry 回傳整份 profile；選用欄位 visual_templates 為工程圖解建議圖組、deck_focus 為簡報財務與競爭頁重點。Kevin 模型只開放 general、growth-manufacturing、semiconductor、semiconductor-equipment、datacenter-networking、osat。網通、交換器、伺服器網卡公司用 datacenter-networking；封測、純測試廠用 osat（含情境 P/B 供景氣谷底參考）；兩者都不套 semiconductor-equipment。ATE、探針卡等測試設備與耗材供應商仍屬設備，不用 osat。

## 工程圖解（visual-build／visual-outline／visual-check）
SVG 的 <text> 依賴檢視端字型：Drive 預覽、郵件、沒裝思源黑體的電腦會整段空白或豆腐字。本包輸出的 SVG 一律把文字轉成字形外框（<defs> 每字一份、<use> 重複引用），任何檢視器都能顯示；可編修母檔是 原始碼/*.json。
diagram spec：{"id":"01","name":"系統架構總覽","title":"…","subtitle":"…","source":"2025 年報 p.70–74","illustrative":true,"palette":"07"（省略用 deck_style）,"elements":[…]}。
elements：box {id,x,y,w,h,title,lines[],style: primary|muted|solid|secondary}；arrow {from,to} 或 {points:[x1,y1,x2,y2]}，可加 label、dash、color: secondary；lane {x,y,w,h,label}；line {points:[…],color,width}；text {x,y,text,size,anchor,weight,color}。畫布預設 1600×900，頁首標題、頁腳來源與「示意圖，非公司原圖」自動加上。source 必須含頁碼、網址或公告。
字型順序：--font-dir／KEVIN_FONT_DIR（可放 Noto Sans TC 的 otf／ttf，或 Google Fonts 切片 woff2 的 regular、bold 子資料夾）→ 已安裝的 Noto Sans TC → 微軟正黑體（msjh.ttc／msjhbd.ttc）→ 蘋方 → fontconfig；另補 Segoe UI／Arial／DejaVu 的希臘字母與符號。缺字報錯不輸出。
visual-outline 不帶 --file 時處理 工程圖解/*.svg（原地轉外框）並重產 PNG預覽；結果寫 工程圖解/驗證紀錄.json。

## 整合簡報（set-deck-style／deck-build／deck-check／deck-fonts）
deck_style 存在 config.json：palette 01–10、font A/B/C（同 ppt-style-picker），中文字型預設 cjk_portable（A：新細明體；B／C：微軟正黑體），--cjk-font 可改。profiles/deck_styles.json 為配色字型資料。
deck spec：{"topic":"產品供應鏈與工程競爭分析","asof":"YYYY-MM-DD","default_source":"…","slides":[…]}，最後一頁必須 closing。slide 型別：
title {title,subtitle,note}｜section {title,subtitle}｜bullets {title,bullets:[str 或 [子項…]],takeaway?,source?}｜cards {title,cards:[{title,body}] 1–4}｜kpi {title,stats:[{value,label,note}] 1–4,bullets?}｜image {title,image:"工程圖解/PNG預覽/01_x.png",caption}｜chart {title,chart: column|bar|line|doughnut|pie,categories,series:[{name,values}],number_format,takeaway?,chart_title?}｜table {title,columns,rows}｜closing {title,bullets,disclaimer?}。
相對路徑以研究 root 為基準。輸出 整合簡報/{公司}{代碼}_{topic}_{N}頁_{日期}.pptx；--pdf 需 LibreOffice（含 Impress），無則 render_qa=skipped。deck-check 檢查：物件超出頁面、可能溢字、長條圖數值軸未從 0 起算、缺來源頁碼、最後一頁缺非投資建議，並列出實際字型。

## Google Drive 同步（set-storage／drive-sync／drive-record）
config.storage：drive_folder（My Drive 內相對路徑，可用 {short}{name}{ticker}{market}；init 預設 投資組合-台股/{short}{ticker}/{short}{ticker}研究）、local_sync_root（Google Drive 桌面版的本機根目錄，例 G:/我的雲端硬碟；雲端環境留空）、connector_max_bytes（預設 100000）。
drive-sync 以 SHA256 比對 Drive同步紀錄.json 找出新增／修改檔（排除 runs/、暫存檔、紀錄本身）。local_sync_root 存在時為 local_sync 模式：--apply 複製並驗雜湊後記錄；否則為 connector 模式：.md/.json/.html/.svg/.csv/.txt 且不超過上限者標 via=connector（宿主用 Drive 連接器上傳到 drive_path），其餘標 via=manual 並寫 待手動上傳.md；上傳後 drive-record 標記（可附 --file-id）。Drive 連接器只能新增檔案、改名與搬移，不能覆寫內容：已修改的檔案（plan 列 replace_drive_file_id）先上傳新檔，再把舊檔移到同層 `_舊版/`，不刪除。永不刪除 Drive 檔案；本機已刪的列 removed_locally。drive_folder 改變時全部視為新檔。

## 缺口與待下載（gaps／coverage-set）
gaps 依截止日推算應已公告的法定文件（一般業：年度財報 3/31、Q1 5/15、Q2 8/14、Q3 11/14；年報以 6/30 為檢查點，實際依股東會日期），與 分類PDF／索引／證據庫比對（文件鍵＝類別＋期別＋語言），未持有者列 MOPS 代碼、discover 參數（kind、ROC 年）與預期檔名；另列 blocked／missing／metadata 證據與未驗證身分。手動缺口（無 auto 標記）保留，自動項每次重算。coverage-set 記錄部分覆蓋（已讀頁、總頁、缺頁）。輸出 缺口清單.json 與 待下載清單.md。金融保險業與外國發行人期限不同，需手動調整。

## README 自動區塊（readme）
README 以 <!-- kevin:auto:start --> … <!-- kevin:auto:end --> 包住自動區塊：成果入口（依實際檔案）、工程圖解是否仍有活字、分類PDF 份數、缺口數、Drive 資料夾與未同步數。區塊外的文字不動；舊 README 沒有標記時插在標題後。

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
  "price":500,"price_date":"2026-09-30",
  "anchor":{"category":"potential","trailing_pe":40,"growth_ttm":0.2,"growth_prior":0.6,"coverage":0.9,"excluded_themes":["記憶體"],"market_pe":25,"market_median_pe":17,"asof":"2026-09-30","source":"錨定ETF工作表（合成示例）"}}}
```
回傳scenarios.A（主要）、選用的scenarios.B、earnings_quality、anchor（b、門檻、剔除記憶體）、warnings、flags（景氣高峰、低基期）。v3.7b：b＝ETF落後PE÷(1+G_TTM)×M_adj，門檻＝同一ETF的G_FY，Δ上限200。anchor可改寫{"category":"cpo","values":"profile"}採外掛內建的最近已知值（會警示）。溢價用target_premium，只乘模型價；雙層錨定欄位（etf_pe、ratio_p／ratio_q、base_pe_p／base_pe_q、base_pe_low／base_pe_high）與multiplier（≠1）會被拒絕並提示新欄位。

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
