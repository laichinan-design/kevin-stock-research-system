---
name: kevin-model
description: 研究流程中的估值步驟（通常由 research-router 呼叫）：在已建立的研究資料夾內選擇估值方法、執行 Kevin v3.7b（ETF 隱含成長錨定，剔除記憶體題材股）或情境計算，並更新已映射的單一股票 Excel 副本。不處理對話內快速估值（kevin-stock-pricing-model）或整本投資組合月度更新（update-portfolio）。
---

# kevin-model

先讀 ../../references/contract.md 與 ../../references/kevin-model.md。不讀固定股票設定。使用者模型先audit-model，再建立並核對examples/model-mapping.template.json；必須確認security、唯一股票鍵、SHA256、欄名、單位、公式摘要。
update-model只改新副本且每筆changes有security/source_id/asof/basis；公式不能經一般輸入通道改寫。版本漂移重新映射。recalculate使用獨立目錄，之後驗快取與獨立算術，不冒稱Microsoft Excel實機驗算。
從產業candidate_methods選擇有資料且適用的方法。value支援kevin_legacy（方法代號沿用；預設計算為 Kevin v3.7b ETF 隱含成長錨定）、scenario_pe、scenario_pb、nav；倍數及折價需可追溯假設。
Kevin請求依examples/kevin-valuation.template.json：anchor 填 category、剔除記憶體題材股後的 ETF 落後本益比 etf_pe_trailing、內涵成長 etf_growth_ttm 與 etf_growth_fy、大盤 P/E 與 10 年中位 P/E，並附 asof、source 與 excluded_themes（優先取自每月 Kevin目標價_YYYY_MM.xlsx 工作表「錨定ETF」，profiles/anchors.json 只是最新已知值，逾 45 天須更新）；基準本益比 b = 落後PE ÷（1＋G_TTM）× M_adj（各類用自己的 ETF），超額門檻＝同一類別 ETF（剔除記憶體）的 etf_growth_fy（未填時套 anchors.json 該類別最新已知值；hurdle_growth 僅供單次覆寫），個股只對超過門檻的部分 Δ 加溢價（Δ 上限 200，Δ<0 折減保守腿）；成長 > 300% 標示低基期，交使用者判斷，記憶體股等特殊個案亦同；提供估值截止日收盤價 price，股價 ÷ EPS < 8 視為景氣高峰；舊版 ratio_p／ratio_q 與 base_pe_p／base_pe_q 只在明示 anchor_method=legacy_dual_anchor 時用來重現舊 workbook。淨利率用earnings_quality逐項列非經常性，占稅前≥10%須明確選帳面或本業；基期EPS若調整須附原值與理由；有近月營收時加run_rate情境B，A／B並列，提前拉貨或併購只標旗標。溢價只用target_premium乘在模型價，不可乘在EPS。
Kevin不適用時保留not_applicable並繼續研究，不自動改填目標價。DCF等尚無計算器不得宣稱已實作。
