---
name: kevin-model
description: 研究流程中的估值步驟（通常由 research-router 呼叫）：在已建立的研究資料夾內選擇估值方法、執行 Kevin v3.7b（ETF 內涵成長錨定）或情境計算，並更新已映射的單一股票 Excel 副本。不處理對話內快速估值（kevin-stock-pricing-model）或整本投資組合月度更新（update-portfolio）。
---

# kevin-model

先讀 ../../references/contract.md 與 ../../references/kevin-model.md。不讀固定股票設定。使用者模型先audit-model，再建立並核對examples/model-mapping.template.json；必須確認security、唯一股票鍵、SHA256、欄名、單位、公式摘要。
update-model只改新副本且每筆changes有security/source_id/asof/basis；公式不能經一般輸入通道改寫。版本漂移重新映射。recalculate使用獨立目錄，之後驗快取與獨立算術，不冒稱Microsoft Excel實機驗算。
從產業candidate_methods選擇有資料且適用的方法。value支援kevin_legacy（v3.7b ETF內涵成長錨定）、scenario_pe、scenario_pb、nav；倍數及折價需可追溯假設。
Kevin請求依examples/kevin-valuation.template.json：anchor放類別ETF（0050／00891／00935）剔除記憶體後的落後PE、G_TTM、G_FY與大盤PE，附asof與source（優先當月「錨定ETF」工作表；讀不到才用values=profile並標日期）；必填price與price_date；門檻預設同一ETF的G_FY，覆寫須附hurdle_source；淨利率用earnings_quality逐項列非經常性，占稅前≥10%須明確選帳面或本業；基期EPS若調整須附原值與理由；有近月營收時加run_rate情境B，A／B並列，提前拉貨或併購只標旗標。溢價只用target_premium乘在模型價，不可乘在EPS。
Kevin不適用時保留not_applicable並繼續研究，不自動改填目標價。DCF等尚無計算器不得宣稱已實作。
