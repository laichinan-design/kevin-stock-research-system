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
