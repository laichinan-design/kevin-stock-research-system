# Kevin 模型 v3.7b（ETF 內涵成長錨定，plugin 0.8.1）
選用模型，只適用正盈餘的成長型企業（產業模板 growth-manufacturing、semiconductor、semiconductor-equipment、datacenter-networking、osat、general）。循環股、金融、資產型、虧損型改用其他方法。結果是情境計算，不是交易訊號。口徑與帳戶 skill `kevin-stock-pricing-model` v3.7b 一致。

## 公式
- 情境A年化營收 = revenue_ytd × 12 ÷ months
- N（預期 EPS）= 年化營收 × 合併淨利率 × owner_ratio ÷ capital_thousands × par；N ≤ 0 → not_applicable
- O（成長率）= N ÷ previous_eps − 1；previous_eps ≤ 0 時以 100% 計並警示
- Δ（超額成長，百分點）=（O − hurdle_growth）× 100
- Δ ≥ 0：P保守 = b + √min(Δ, 200)；P樂觀 = b + min(Δ, 200)^(2/3)
- Δ < 0：P保守 = b × clip((1+O) ÷ (1+hurdle), 0.25, 1)；P樂觀 = b；警示「成長低於錨定 ETF」
- 景氣高峰（price ÷ N < 8，自動判斷）：EPS 改用 (N + max(J,0)) ÷ 2，兩腿 = b ÷ (1 + hurdle)；使用者查證後可用 cycle_peak（true／false）覆寫，須附 cycle_reason
- 低基期：非景氣高峰且 O > 300% → low_base=true 並列 flags，數字不自動調整，由使用者判斷
- 模型價 T = EPS × (P保守 + P樂觀) ÷ 2；Δ 很小時 √ 腿可能高於 2/3 次方腿，兩腿排序後顯示並警示
- target_premium（選用，0–3）只乘在模型價，另列 model_value_with_premium；EPS、成長率、本益比都不含溢價
- excess_cap 選填，預設 200；改值輸出警示

## ETF 內涵成長錨定（inputs.anchor）
- 錨定 ETF：portfolio（投資組合）→ 0050、cpo（CPO概念）→ 00891、potential（潛力股）→ 00935；category 也接受中文名稱。給 etf 時必須與類別一致
- b = ETF 加權落後 PE ÷ (1 + G_TTM) × M_adj（即 ETF 對今年預期 EPS 的前瞻 PE × M_adj）
- hurdle_growth 預設 = 同一 ETF 的 G_FY（去年 → 今年預期）；G_TTM 只用來把落後 PE 換成前瞻 PE，不可拿來當門檻
- M = 大盤 PE ÷ 10 年中位 PE（market_pe＋market_median_pe，或 market_pe_ratio 擇一）；M > 1.3 → 0.85，M < 0.8 → 1.15，其餘 1.0（邊界值不調整）
- 摘要模式：trailing_pe、growth_ttm、growth_prior、coverage（選填，未給列警示）、excluded_themes（應含「記憶體」，未註明列警示）、excluded_count（選填）
- 成分股模式：constituents 每列 weight（全 ETF 權重）、price、eps_ttm、eps_forecast、eps_prior、code（或 theme）；盈餘殖利率加權後取倒數；記憶體題材股（profiles/anchors.json memory_codes，21 檔）自動剔除、剩餘權重重新歸一；exclude_memory=false 會警示不符 v3.7b。金融股等算不出預期 EPS 者 eps_forecast = eps_prior = eps_ttm（成長 0）
- anchor.values="profile"：採 profiles/anchors.json 的最近已知值（2026-10-03，剔除記憶體）並警示，正式估值應改用當月「錨定ETF」工作表
- 必填 asof 與 source；asof 晚於估值截止日直接拒絕，超過 45 天列警示
- 門檻單次覆寫：inputs.hurdle_growth（小數）＋ hurdle_source（必填）＋ hurdle_asof（選填），輸出警示
- 不用 anchor 時可直接給 base_pe ＋ hurdle_growth ＋ anchor_source（三者皆必填）；anchor 與 base_pe 只能擇一
- 必填 price 與 price_date（price_date 不得晚於截止日）：景氣高峰判斷與 upside 需要股價

## 2026-10-03 最近已知值（剔除記憶體，profiles/anchors.json last_known）
| 類別 | ETF | 落後 PE | G_TTM | 前瞻 PE | M_adj | b | G_FY＝門檻 |
|---|---|---|---|---|---|---|---|
| portfolio | 0050 | 29.2295 | 18.31% | 24.7053 | 0.85 | 20.9995 | 48.50% |
| cpo | 00891 | 38.6352 | 22.30% | 31.5912 | 0.85 | 26.8525 | 52.89% |
| potential | 00935 | 41.8694 | 22.34% | 34.2248 | 0.85 | 29.0911 | 60.20% |

## 淨利率與少數股權
- 淨利率一律合併口徑（本期淨利 ÷ 營收）；少數股權只透過 owner_ratio = 歸母淨利 ÷ 合併淨利 扣除。用歸母淨利率再乘 owner_ratio 會重複扣除，程式拒絕
- owner_ratio > 1（少數股權分攤虧損）須 nci_loss_verified=true
- consolidated_margin（附 margin_basis=consolidated）與 earnings_quality 擇一
- 股本 capital_thousands 取官方實收資本額，不得以淨利 ÷ EPS 反推

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
- 淨利率用最近一季（consolidated_margin 或 earnings_quality）；margin_choice 未指定時沿用情境A；b 與門檻同情境A
- pull_in_suspected=true（客戶提前拉貨）與 inorganic_monthly（併購帶來的月營收）只產生旗標，不自動調整數字
- 情境A為主要結果；B 並列，b_vs_a 顯示差距；B 不適用時只標 not_applicable，不影響 A
- 散熱／CPO／先進封裝設備：線性年化可能低估 H2 ramp，應並列情境 B

## 輸出（scenarios.A／B）
eps、previous_eps、growth、hurdle_growth、delta_pp、delta_capped_pp、excess_cap、branch（excess_growth／below_anchor_growth／cycle_peak_auto／cycle_peak_confirmed）、cycle_peak、low_base、effective_eps、base_pe、pe_conservative、pe_optimistic、price_conservative、price_optimistic、model_value、forward_pe_at_price、upside、target_premium（≠1 時另列 model_value_with_premium、upside_with_premium）。頂層另有 anchor（trailing_pe、growth_ttm、growth_prior、forward_pe、m_ratio、m_adj、base_pe、coverage、excluded_themes、excluded、hurdle_source、age_days）、warnings、flags。

## 0.7.0 → 0.8.1 遷移
- 雙層錨定停用：anchor 的 etf_pe／ratio_p／ratio_q 與輸入 base_pe_p／base_pe_q（以及更早的 base_pe_low／base_pe_high）一律拒絕並提示改用 ETF 內涵成長錨定
- 新增必填 price、price_date；anchor 必填 source
- 成長率不再要求非負：Δ<0 走保守腿折減；previous_eps ≤ 0 以 100% 計
- 輸出欄位 pe_p／pe_q／price_p／price_q 改名為 pe_conservative／pe_optimistic／price_conservative／price_optimistic；model 名稱改為 kevin_etf_implied_growth_v3.7b
- 0.7.0 以前存檔的 valuation JSON 是舊口徑，重算時要補 price、price_date 與新的 anchor 摘要
