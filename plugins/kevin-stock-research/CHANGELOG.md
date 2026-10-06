# 0.8.1 — 2026-10-06
- Kevin 模型改為 v3.7b（ETF 內涵成長錨定），與帳戶 skill kevin-stock-pricing-model／update-portfolio v3.7b 同口徑；雙層錨定（ETF PE × 0.75／0.55 等比例）停用。
  - 基準 b ＝ ETF 加權落後 PE ÷ (1 + G_TTM) × M_adj；超額門檻 ＝ 同一 ETF 的 G_FY；Δ ＝ (O − 門檻) × 100，上限 200（excess_cap 可調，改值警示）。
  - Δ ≥ 0：保守 b＋√Δ、樂觀 b＋Δ^(2/3)；Δ < 0：保守 b×clip((1+O)/(1+門檻),0.25,1)、樂觀 b；price ÷ N < 8 自動景氣高峰（EPS 取兩年平均、兩腿 b÷(1+門檻)，cycle_peak 覆寫須附理由）；O > 300% 標 low_base；預期 EPS ≤ 0 不給目標價；去年 EPS ≤ 0 成長以 100% 計。
  - anchor 支援摘要（trailing_pe、growth_ttm、growth_prior、coverage、excluded_themes）與成分股明細（盈餘殖利率加權、記憶體題材股 21 檔自動剔除並重新歸一）；category 接受中文名稱並檢查 ETF 一致；values="profile" 採內建 2026-10-03 最近已知值（b 20.9995／26.8525／29.0911，門檻 48.50%／52.89%／60.20%）並警示；hurdle_growth 覆寫須附 hurdle_source；直接給 base_pe＋hurdle_growth 須附 anchor_source。
  - 新增必填 price、price_date；anchor 必填 source。輸出欄位改為 pe_conservative／pe_optimistic／price_conservative／price_optimistic，另列 delta_pp、branch、cycle_peak、low_base、upside；model 名稱 kevin_etf_implied_growth_v3.7b。舊欄位 etf_pe、ratio_p／ratio_q、base_pe_p／base_pe_q、base_pe_low／base_pe_high 一律拒絕並提示遷移。
- profiles/anchors.json 改為 v3.7b 參數（M_adj 規則、上限、低基期、景氣高峰、記憶體代碼、最近已知值）；validate_package 改檢查新結構；測試確認 profile 常數與程式一致。
- 回歸案例改為 skill v3.7b 範例：貝爾威勒 T ≈ 1,743（×1.5 ≈ 2,615）、松川 440／513／642、矽格 CPO 28.32／28.52。測試 123→131。
- 文件：kevin-model.md 重寫（含 0.7.0 → 0.8.1 遷移）、cli.md 範例、contract、capabilities、README、kevin-model skill、估值模板。
- 0.8.0 未單獨發行，版本號直接跳到 0.8.1。

# 0.7.0 — 2026-10-02
- 新產業模組 osat（半導體封裝測試，含純測試廠）：KPI 為測試／封裝營收結構、應用別占比、稼動率與機台產能、capex／折舊／EBITDA 率、經營槓桿、客戶結構、新技術測試（先進封裝、HBM、矽光子、CPO）、自由現金流與少數股權；guards 涵蓋折舊固定成本與新廠投產、客戶包產能不等於長約、商業模式不可直接套倍數、客戶提供機台（consigned tester）、美元匯兌與基期 EPS、擴產期現金流、新技術占比不得推估與 H2 ramp 情境 B、子公司少數股權口徑；同業規則分純測試、封測一體、先進封裝，記憶體封測另列，ATE／探針卡供應商不列同業。candidate_methods 另開 scenario_pb 供景氣谷底參考。init／set-industry 可用，Kevin 模型開放，產業模板 9→10。封測公司不再套 semiconductor 通用或 semiconductor-equipment。
- research-router、engineering-visuals、cli.md、capabilities.md 補 osat 分流與圖組。測試 122→123。

# 0.6.0 — 2026-10-02
- 新產業模組 datacenter-networking（資料中心網通與交換器 ODM／JDM）：KPI 為速率世代組合、交換晶片平台與客戶專案、客戶集中度、產品組合、毛利率／營益率結構（料件 pass-through）、存貨與營業現金流、產能地點；guards 涵蓋 pass-through、世代轉換備料、未公告專案與 CPO／LPO、匯兌、單一客戶；同業規則分白牌 ODM／JDM、品牌、EMS。init／set-industry 可用，產業模板 8→9。網通公司不再套 semiconductor-equipment。
- 產業 profile 新增選用欄位 visual_templates（工程圖解建議圖組）與 deck_focus（整合簡報重點）；semiconductor-equipment 同步補上。engineering-visuals 改為優先依 profile 選圖，integrated-deck 依 deck_focus 安排財務與競爭頁。
- 修正：semiconductor-equipment 模板列有 kevin_legacy，但 value 仍回 industry not supported；改以 KEVIN_INDUSTRIES 判定，設備與網通都可跑 Kevin 模型，循環／金融／資產／虧損型仍擋。
- validate_package 檢查每個產業 profile 的 id、必要欄位、估值方法名稱與選用欄位格式；測試確認 profile 檔案與程式登記一致。測試 119→122。

# 0.5.0 — 2026-10-02
- Google Drive 同步（scripts/storage.py）：config.storage（drive_folder、local_sync_root、connector_max_bytes），init 預設 投資組合-台股/{簡稱}{代碼}/{簡稱}{代碼}研究；set-storage、drive-sync（SHA256 變動偵測，dry-run 預設；本機 Google Drive 桌面版直接複製並驗雜湊，雲端則分 connector／manual 並寫 待手動上傳.md）、drive-record（上傳後標記，可存 Drive file id）；永不刪 Drive 檔，資料夾改變時全部重送。
- 缺口與待下載（scripts/gaps.py）：gaps 依一般業法定期限推算應公告的年度財報、季報、年報，與分類PDF／索引／證據庫比對，列 MOPS 代碼、discover 參數與預期檔名；併列被擋來源、未驗證身分；手動缺口保留。coverage-set 記錄部分覆蓋。輸出 缺口清單.json、待下載清單.md。
- README 自動區塊（scripts/readme.py）：成果入口、工程圖解活字檢查、分類PDF 份數、缺口、Drive 狀態依實際檔案重產，區塊外文字不動；init 改用此產生。
- 新產業模板 semiconductor-equipment（設備與廠務自動化：裝機量、相容機型、劇本／模組、客戶 capex、驗收認列與在製品、軟硬體毛利）；set-industry 指令。產業模板 7→8。
- repo 內發行工具：tools/build_release.py 從 repo 組出 dist/plugin-release-<版本>/（與 Drive 同結構），release/ 放 START-HERE、install-openai.ps1、Codex catalog；版本一致性含 START-HERE。
- skills：router、data-acquisition、document-organizer、report-validation 加入 gaps／coverage-set／readme／drive-sync 步驟。測試 112→119。

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
