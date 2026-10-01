# Kevin 雙層錨定模型 0.2.1
選用模型，只適用正盈餘、非負成長的企業（產業模板 growth-manufacturing、semiconductor、general）。循環股、金融、資產型、虧損型改用其他方法。結果是情境計算，不是交易訊號。

## 公式
- 情境A年化營收 = revenue_ytd × 12 ÷ months
- EPS = 年化營收 × 合併淨利率 × owner_ratio ÷ capital_thousands × par
- 成長率 g = EPS ÷ previous_eps − 1；g < 0 時 not_applicable
- PE_P = base_pe_p + √(g×100)；PE_Q = base_pe_q + (g×100)^(2/3)
- 模型價 = EPS × (PE_P + PE_Q) ÷ 2
- target_premium（選用，0–3）只乘在模型價，另列 model_value_with_premium；EPS、成長率、本益比都不含溢價

## 雙層錨定（inputs.anchor）
- base_pe_p = ETF PE × ratio_p × M_adj；base_pe_q = ETF PE × ratio_q × M_adj
- M = 大盤 PE ÷ 10 年中位 PE；M > 1.3 → 0.85，M < 0.8 → 1.15，其餘 1.0（邊界值不調整）
- category 預設比例見 profiles/anchors.json：portfolio（0050，0.75／0.55）、cpo（00891，0.85／0.62）、potential（00935，0.85／0.62）；明列 ratio_p／ratio_q 時以明列值為準
- 必填 etf_pe、market_pe、market_median_pe、asof；asof 晚於估值截止日直接拒絕，超過 45 天列警示
- anchor 與 base_pe_p／base_pe_q 只能擇一

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
- 淨利率用最近一季（consolidated_margin 或 earnings_quality）；margin_choice 未指定時沿用情境A
- pull_in_suspected=true（客戶提前拉貨）與 inorganic_monthly（併購帶來的月營收）只產生旗標，不自動調整數字
- 情境A為主要結果；B 並列，b_vs_a 顯示差距；B 不適用時只標 not_applicable，不影響 A

## 0.2.0 → 0.2.1 遷移
- multiplier（乘在 EPS）已移除：它同時灌高成長率與本益比，×1.5 實際讓目標價放大約 1.92 倍。改用 target_premium；multiplier=1 仍接受
- base_pe_low／base_pe_high 改名為 base_pe_p（√ 項）／base_pe_q（2/3 次方項）；使用舊名稱直接拒絕並提示新名稱
- 0.2.0 的 kevin_legacy 請求須補 margin 口徑或 earnings_quality，否則輸出盈餘品質未檢查警示
