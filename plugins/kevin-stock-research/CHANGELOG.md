# 0.4.0 — 2026-10-02
- 新技能 engineering-visuals 與 scripts/visuals.py：diagram spec（box／arrow／lane／line／text）產生工程圖，頁首頁腳、來源頁碼、示意圖標示自動加上；SVG 文字一律轉成字形外框（修正 Drive 預覽與未安裝思源黑體時文字不顯示），原始碼 JSON 為可編修母檔，另產 PNG預覽。字型自動探測（Noto Sans TC → 微軟正黑體 → 蘋方 → fontconfig）並以 Segoe UI／Arial／DejaVu 補 μ、Ω、±；缺字直接報錯。指令 visual-build／visual-outline（修舊 SVG）／visual-check。
- 新技能 integrated-deck 與 scripts/deck.py：profiles/deck_styles.json（ppt-style-picker 10 配色×3 字型）、set-deck-style 寫入 config；deck spec 九種版型，python-pptx 原生可編輯圖表（長條圖數值軸強制從 0）；中文字型預設微軟正黑體確保顯示；deck-check 檢查溢字、出界、0 軸、來源、非投資建議；--pdf 經 LibreOffice 匯出；deck-fonts 修既有簡報字型。
- research-router full：…→fundamental-research→engineering-visuals→kevin-model→integrated-deck→report-validation；MODES full 加 pdf-library／engineering-visuals／integrated-deck 步驟。
- visual-outline 原地轉外框時，活字原檔保留在 工程圖解/原始碼/*_活字原檔.svg；已轉過的檔案略過。
- 測試 103→112。
- requirements 加 fonttools、brotli、cairosvg、python-pptx、Pillow。技能 8→10。

# 0.3.0 — 2026-10-02
- 研究root layout：init／Store 增建 分類PDF/01–08、工程圖解/{PNG預覽,實物設備詳解版,工藝精度圖例增補版}、整合簡報；onboard 另產 README.md（成果入口）與 缺口清單.json。既有root開啟時自動補建空資料夾，不動既有檔案。
- 新指令 classify-pdfs（scripts/library.py）：8類命名規則（年報依會計年度、全年財報不標Q4、Q2／Q3標含累計、會議與報告用YYYY-MM-DD、外部研究發布機構_日期_主題_語言）；同SHA256只留一份並合併來源；同名不同SHA全部加_來源版SHA前8碼；硬連結不複製；dry-run預設，--apply輸出 PDF分類索引.json／.xlsx、PDF分類目錄.html、整理說明.md、空類別 目前無檔案.txt。索引與健策3653既有格式相容。
- 新指令 dedupe-check；ingest 下載前自動略過已持有文件（SHA256、原始檔名、文件鍵；MOPS檔名與分類檔名互通；可吃Drive清單 --known），--force 才重抓。mops.pending() 供下載前分流。
- MOPS代碼表：AI1（YYYYQQ，04為全年）、F04（中文年報）、FE4（英文年報）；其他代碼不猜。
- 測試由89增至103。

# 0.2.2 — 2026-10-01
- 只改技能描述（程式與計算不變）：research-router限定為建立研究資料夾的完整研究流程入口，其餘七個技能標為研究流程步驟；kevin-model不再承接對話內快速估值與整本投資組合月度更新，分別交給帳戶技能kevin-stock-pricing-model與update-portfolio，避免觸發重疊。

# 0.2.1 — 2026-10-01
- Kevin模型：倍率溢價改為target_premium，只乘在模型價；移除乘在EPS的multiplier（原寫法同時灌高成長率與本益比，×1.5實際放大目標價約1.92倍）。multiplier≠1直接拒絕並提示改法。
- Kevin模型：新增雙層錨定（ETF PE×比例×M_adj），profiles/anchors.json提供投資組合／CPO／潛力股三類比例；錨定日期晚於截止日拒絕、逾45天警示。base_pe_low／base_pe_high改名base_pe_p／base_pe_q。
- Kevin模型：新增盈餘品質檢查，非經常性（股票評價、一次性處分、匯兌）逐項列示並算本業淨利率；占稅前≥10%須明確選帳面或本業，5–10%列警示。淨利率限合併口徑，少數股權只由owner_ratio扣除。
- Kevin模型：基期EPS可標normalized，須附原值與理由，輸出兩種成長率。
- Kevin模型：新增情境B（近月營收動能×最近一季淨利率），與情境A並列；提前拉貨與併購貢獻只標旗標。
- general產業模板開放kevin_legacy；循環、金融、資產型、虧損型仍不適用。
- 新增Claude Code用.claude-plugin/marketplace.json，並以claude plugin validate驗證。
- 回歸測試加入公開財報數字案例（錨定三類基準、溢價、本業淨利率、基期調整、情境B），測試數由72增至89。

# 0.2.0 — 2026-10-01
- 一份核心，ChatGPT／Codex／Claude manifests，8個技能（原7個＋總入口）。
- 多市場普通股設定、每股root隔離、7種產業模板、6種研究模式。
- 修復空來源full、流量科目白名單、缺交易日累計、錯股票Excel寫入、跨股監控狀態。
- 工作簿SHA256及股票鍵映射、財務facts schema及look-ahead防護。
- Kevin適用性分流、情境P/E／P/B／NAV、同幣別合併資金試算。
- SQLite原子監控outbox及重試去重；批次方案不預留現金、不自動下單。
- 移除私人Drive識別、本機路徑及固定健策設定。舊版研究須dry-run遷移。
- TPEX／美股live adapter未實作；已支援標準化市場資料匯入。排程交由宿主且預設關閉。
