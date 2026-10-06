# Kevin 模型 v3.7b（ETF 隱含成長錨定，0.8.0 起預設；0.8.1 起 v3.7b）
選用模型，只適用正盈餘企業（產業模板 growth-manufacturing、semiconductor、general、semiconductor-equipment、datacenter-networking、osat）。循環股、金融、資產型、虧損型改用其他方法。結果是情境計算，不是交易訊號。估值方法代號仍為 kevin_legacy（產業模板沿用的方法 id），與下方「舊公式 legacy_dual_anchor」無關。

## 為什麼改公式
- ETF 落後本益比已經反映市場對成分股的成長預期；個股再對「全部」成長率加本益比溢價，等於重複計算成長。
- 舊版固定比例 0.55／0.75（CPO、潛力股 0.62／0.85）不會隨 ETF 內涵成長變動，市場預期變了基準本益比卻不動。
- workbook 手填的 0050 本益比 22 已過時：2026-09-10 依持股實算為 28.4。
- v3.7 先把 ETF 本益比換成前瞻口徑當基準，個股只對「超過 ETF 內涵成長」的部分加溢價。
- v3.7b（2026-10-06）：記憶體超級循環（華邦電 EPS 0.88→17.8、南亞科 2.13→58.7）把 00891／00935 的內涵成長灌高到 83.4%／80.4%，CPO 與潛力股的超額成長被壓低。因此 ETF 錨定與超額門檻都剔除記憶體題材股後重算（門檻＝類別 ETF 自身的 G_FY：48.50%／52.89%／60.20%）、Δ 上限提高到 200，並對成長 > 300% 標示低基期。曾考慮三類統一用 0050 的 G_FY，使用者 2026-10-06 決定不採用。

## 公式
- 情境A年化營收 = revenue_ytd × 12 ÷ months
- EPS = 年化營收 × 合併淨利率 × owner_ratio ÷ capital_thousands × par（不乘任何倍率）
- 成長率 g = EPS ÷ previous_eps − 1；previous_eps 必須 > 0，≤ 0 時直接拒絕（成長率無意義，與 0.7.0 相同），請改用其他估值方法或以 normalized 基期並附說明
- 基準本益比 b = etf_pe_trailing ÷ (1 + etf_growth_ttm) × M_adj（ETF 持股剔除記憶體題材股後計算；或直接提供 base_pe，須已含 M_adj），各類用自己的 ETF
- 超額門檻：預設 = 類別 ETF 自身的 etf_growth_fy（剔除記憶體）；hurdle_growth 只用於單次覆寫（輸出警示）
- 景氣高峰：有提供 price 且 price ÷ EPS < 8 → EPS* =（EPS + max(previous_eps, 0)）÷ 2，成長率視為 0，兩腿本益比 = b ÷ (1 + hurdle_growth)；輸出 peak_earnings=true 並加旗標
- 其他情況：超額成長 Δ =（g − hurdle_growth）× 100（百分點），上限 cap = excess_cap（預設 200）
  - Δ ≥ 0：PE_cons = b + √min(Δ, cap)；PE_opt = b + min(Δ, cap)^(2/3)
  - Δ < 0：PE_cons = b × clip((1 + g) ÷ (1 + hurdle_growth), 0.25, 1)；PE_opt = b
- 低基期：非景氣高峰且 g > 3（300%）→ low_base=true，旗標「低基期：預期 EPS 成長 X%，需人工判斷（剔除或改用兩年平均 EPS）」；數字不自動調整，記憶體股等特殊個案由使用者判斷
- price_cons = EPS* × PE_cons；price_opt = EPS* × PE_opt；模型價 =（price_cons + price_opt）÷ 2（非高峰時 EPS* = EPS）
- target_premium（選用，0–3）只乘在模型價，另列 model_value_with_premium；EPS、成長率、本益比都不含溢價
- 未提供 price 時不做景氣高峰檢查，輸出警示；研究報告應提供估值截止日收盤價

輸出欄位（scenarios.A／B）：eps（計算值）、eps_valuation（實際用於計價的 EPS*）、growth、growth_used、base_pe、etf_growth_fy、hurdle_growth（實際門檻）、hurdle_source（etf_growth_fy／hurdle_growth_override）、delta（未設上限）、delta_capped、delta_cap、branch（excess_growth／below_etf_growth／peak_earnings）、peak_earnings、low_base、model_version、price_to_eps、pe_cons、pe_opt、price_cons、price_opt、model_value、model_value_with_premium。

## 錨定（inputs.anchor）
- category 決定 ETF：portfolio（投資組合→0050）、cpo（CPO概念→00891）、potential（潛力股→00935）
- 必填 etf_pe_trailing（ETF 持股剔除記憶體題材股、權重重新歸一後的加權落後本益比 = 1 ÷ Σ 權重 ×（近四季 EPS ÷ 股價））、etf_growth_ttm（G_TTM：近四季 EPS → 預期 EPS）、etf_growth_fy（G_FY：去年全年 EPS → 預期 EPS，類別 ETF 自身）、market_pe、market_median_pe、asof、source；建議附 excluded_themes: ["記憶體"]（未註明時警示）；成長率一律用小數（0.485 = 48.5%）
- 剔除清單（profiles/anchors.json excluded_codes）：2344 華邦電、6770 力積電、3006 晶豪科、5386 青雲、4973 廣穎電通、8096 擎亞、2408 南亞科、2337 旺宏、8299 群聯、3260 威剛、2451 創見、8271 宇瞻、4967 十銓、5289 宜鼎、5351 鈺創、3135 凌航、8112 至上、6265 方土昶、8088 品安、6485 點序、6531 愛普
- 超額門檻解析順序：inputs.hurdle_growth 或 anchor.hurdle_growth（單次覆寫）→ 同一份 anchor 的 etf_growth_fy → profiles/anchors.json 該類別 latest_known.etf_growth_fy（最新已知值）；門檻與 anchor 不同日或逾 45 天時警示
- excess_cap：預設取 profiles/anchors.json 的 excess_cap（200），inputs.excess_cap 可單次覆寫並警示
- 也可直接給 base_pe 與 etf_growth_fy（此時不填 anchor），hurdle_growth 選填覆寫
- M = 大盤 PE ÷ 10 年中位 PE；M > 1.3 → 0.85，M < 0.8 → 1.15，其餘 1.0（邊界值不調整）
- 數值每月變動：優先取自每月輸出檔 投資組合-台股/演算法/Kevin目標價_YYYY_MM.xlsx 工作表「錨定ETF」，source 寫檔名與工作表；asof 晚於估值截止日直接拒絕，超過 45 天列警示
- anchor 與直接輸入的 base_pe／etf_growth_fy 只能擇一

最新已知值（profiles/anchors.json，v3.7b：2026-10-03 收盤、ETF 持股 2026-08-31、剔除記憶體、M_adj 0.85）：

| 類別 | ETF | 剔除檔數 | 落後PE | G_TTM | 前瞻PE | b | G_FY | 超額門檻 |
|---|---|---|---|---|---|---|---|---|
| 投資組合 | 0050 | 1 | 29.229530 | 0.183130 | 24.705260 | 20.999471 | 0.485004 | 0.485004 |
| CPO概念 | 00891 | 2 | 38.635243 | 0.222976 | 31.591182 | 26.852505 | 0.528864 | 0.528864 |
| 潛力股 | 00935 | 2 | 41.869429 | 0.223364 | 34.224825 | 29.091102 | 0.602024 | 0.602024 |

v3.7（0.8.0）舊值：b 20.748211／23.515962／26.557095，各自 G_FY 0.511662／0.834407／0.803965，上限 100（anchors.json latest_known.previous_v3_7）。

回歸驗算（v3.7b）：貝爾威勒 7861（投資組合，EPS 46.34、g 157.4%、Δ 108.9，未達上限 200）PE 31.44／43.81，模型價約 1,743，×1.5 約 2,615；奇鋐（EPS 92.722、J 49.17）PE 27.33／32.71；緯穎 g 25.6% → 17.76／21.00；景氣高峰 → 14.14；矽格（CPO，門檻 52.89%）g 55.1% → 28.34／28.55；松川精密（潛力股，門檻 60.20%）441／513／641；麗臺 g 1,411% → Δ 封頂 200 → 35.14／55.20 並標示低基期。以 excess_cap=100、v3.7 錨定（b 20.748211、G_FY 0.511662）可重現 0.8.0 的 1,692。

## 淨利率與少數股權
- 淨利率一律合併口徑（本期淨利 ÷ 營收）；少數股權只透過 owner_ratio = 歸母淨利 ÷ 合併淨利 扣除。用歸母淨利率再乘 owner_ratio 會重複扣除，程式拒絕
- owner_ratio > 1（少數股權分攤虧損）須 nci_loss_verified=true
- consolidated_margin（附 margin_basis=consolidated）與 earnings_quality 擇一

## 盈餘品質（earnings_quality）
- 欄位：scope=consolidated、revenue、pretax、tax、net_income（合併）、nonrecurring（逐項列示，例：fvtpl 股票評價、disposals 一次性處分、fx 匯兌）
- 本業淨利率 =（稅前 − 非經常性）×（1 − 稅率）÷ 營收
- 非經常性占稅前（取絕對值）：< 5% 乾淨；5–10% 使用帳面時列警示；≥ 10% 必須設定 margin_choice 為 reported 或 core，未設定則 not_applicable 並說明
- 利息收支、權益法損益、各期穩定的其他收入屬經常性，不列入 nonrecurring
- 只提供 consolidated_margin 時，輸出警示「盈餘品質未檢查」

## 基期 EPS（previous_eps）
- previous_eps_basis：reported（預設）或 normalized
- normalized 須附 previous_eps_reported 與 previous_eps_note（調整理由及來源），輸出另列 growth_vs_reported_eps
- 基期被一次性損益壓低時（例如匯損），成長率與本益比會同時放大；報告應並列兩種基期的結果

## 情境B（run_rate，選用）
- 年化營收 = revenue_ytd + 最近月份平均 × (12 − months)；recent_months 至少兩個月，且應為 revenue_ytd 內最近的月份
- 淨利率用最近一季（consolidated_margin 或 earnings_quality）；margin_choice 未指定時沿用情境A；景氣高峰檢查用同一個 price
- pull_in_suspected=true（客戶提前拉貨）與 inorganic_monthly（併購帶來的月營收）只產生旗標，不自動調整數字
- 情境A為主要結果；B 並列，b_vs_a 顯示差距；B 不適用時只標 not_applicable，不影響 A

## 舊公式 legacy_dual_anchor（只供重現舊 workbook）
- 必須明示 anchor_method="legacy_dual_anchor"（放在 inputs 或 inputs.anchor），才接受 base_pe_p／base_pe_q 或 anchor.etf_pe／ratio_p／ratio_q；未明示時程式拒絕並說明 v3.7
- base_pe_p = ETF PE × ratio_p × M_adj；base_pe_q = ETF PE × ratio_q × M_adj；比例預設見 profiles/anchors.json 的 legacy_dual_anchor（0.75／0.55、0.85／0.62）
- PE_P = base_pe_p + √(g×100)；PE_Q = base_pe_q + (g×100)^(2/3)；模型價 = EPS ×（PE_P + PE_Q）÷ 2；g < 0 不適用
- 例：貝爾威勒 base_pe_p 14.025／base_pe_q 10.285 → 模型價約 1,529，×1.5 約 2,294（與 0.2.1–0.7.0 相同）

## 0.8.0 → 0.8.1 遷移（v3.7 → v3.7b）
- inputs.anchor 請改填剔除記憶體後的 ETF 數值（Kevin目標價_YYYY_MM.xlsx「錨定ETF」已有「剔除題材檔數」「超額門檻」欄），並附 excluded_themes: ["記憶體"]
- 超額門檻仍是類別 ETF 自己的 G_FY，但要用剔除記憶體後的值（00891 由 83.4% 降為 52.89%、00935 由 80.4% 降為 60.20%）；hurdle_growth 只在需要單次覆寫時填
- 直接給 base_pe 的請求：照舊給 base_pe 與 etf_growth_fy（剔除記憶體後的值）
- Δ 上限預設 200；要重現 0.8.0 數字可加 excess_cap=100 並用 v3.7 錨定值
- 新輸出 low_base（成長 > 300%）與 hurdle_growth／hurdle_source；model_version 為 v3.7b

## 0.7.0 → 0.8.0 遷移
- 原本的 anchor.etf_pe、ratio_p、ratio_q 或 base_pe_p／base_pe_q 請求：改填 etf_pe_trailing、etf_growth_ttm、etf_growth_fy、source（或 base_pe＋etf_growth_fy）；只想重現舊數字時加 anchor_method="legacy_dual_anchor"
- 建議同時提供 price（估值截止日收盤價），才會做景氣高峰檢查
- 舊版的 pe_p／pe_q 輸出在 v3.7 改為 pe_cons（保守腿）／pe_opt（樂觀腿），price_p／price_q 改為 price_cons／price_opt

## 0.2.0 → 0.2.1 遷移
- multiplier（乘在 EPS）已移除：它同時灌高成長率與本益比，×1.5 實際讓目標價放大約 1.92 倍。改用 target_premium；multiplier=1 仍接受
- base_pe_low／base_pe_high 改名為 base_pe_p（√ 項）／base_pe_q（2/3 次方項）；使用舊名稱直接拒絕並提示新名稱
- 0.2.0 的 kevin_legacy 請求須補 margin 口徑或 earnings_quality，否則輸出盈餘品質未檢查警示
