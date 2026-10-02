---
name: research-router
description: Kevin 股票研究 plugin 總入口：建立每股研究資料夾與證據庫的完整研究、快速研究、研究更新、多股比較、盤後追蹤或部位規劃時使用，例如「完整研究 TWSE:2330」「建立研究資料夾」「盤後追蹤」「部位規劃」。對話內快速估值或加同業改用 kevin-stock-pricing-model；整本投資組合 workbook 月度更新改用 update-portfolio。
---

# research-router

先讀 ../../references/contract.md、../../references/capabilities.md。從使用者要求決定 quick/full/refresh/monitor/compare/position，不把單次查詢升級成自動排程。
辨識市場＋代號＋公司名；若已有對話中的root設定就沿用。否則選使用者專案內獨立market-ticker資料夾。呼叫 scripts/workflow.py --root <root> init；先讀官方身分證據再 verify-identity。補核reporting_currency、fiscal_year_end、industry；未知保留缺口不啟用依賴能力。
執行 plan --mode <mode> --asof YYYY-MM-DD，依計畫使用本外掛其他技能完成工作。計畫產出不是研究完成。並列已實作與unsupported來源；使用宿主瀏覽／下載工具取得證據。
full依data-acquisition（先dedupe-check）→document-organizer（含classify-pdfs）→fundamental-research→kevin-model→report-validation。init已建立分類PDF／工程圖解／整合簡報資料夾與README、缺口清單.json。position才加position-planning；monitor用postclose-monitor；compare驗同口徑、同行業及資料日。讀 ../../references/cli.md取得真正可用指令。
同時多股依序處理；每股失敗記錄缺口，繼續不受影響的股票。不要另開使用者聊天。只在使用者要求時建立排程或更改安裝。
