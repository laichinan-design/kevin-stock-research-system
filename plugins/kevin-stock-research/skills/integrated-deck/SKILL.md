---
name: integrated-deck
description: 研究流程步驟（通常由 research-router 呼叫）：把個股研究整合成 20–28 頁簡報（PPTX＋PDF，原生可編輯圖表），配色字型取自研究資料夾 deck_style；新建前若未設定先跑 ppt-style-picker。
---

# integrated-deck

先讀 ../../references/contract.md、../../references/cli.md 的「整合簡報」節。config 沒有 deck_style 時，先用帳戶技能 ppt-style-picker 讓使用者選配色（01–10）與字型（A/B/C），再 set-deck-style 寫入；之後 refresh 沿用，不重問。
標準大綱：封面與結論 → 公司與產品 → 工程圖解（引用 工程圖解/PNG預覽）→ 供應鏈與競爭 → 財務與估值（Kevin 模型情境 A／B、同業）→ 風險與追蹤 → closing（結論、催化、非投資建議）。每頁一個訊息，標題寫結論不寫主題。產業 profile 有 deck_focus 時，供應鏈與競爭、財務與估值兩段依它安排重點頁。
寫 deck spec（JSON：topic、asof、default_source、slides；type＝title／section／bullets／cards／kpi／image／chart／table／closing），用 deck-build --pdf 產生 整合簡報/{公司}{代碼}_{主題}_{N}頁_{日期}.pptx 與 PDF，結果存 整合簡報/validation.json。
數字只取已驗證 facts 與估值輸出；金額標 NT$ 與單位，比例標期間。圖表用 chart（原生可編輯）：長條圖數值軸從 0 起算，單一系列不加圖例，占比用 doughnut。每頁需來源（slide.source 或 default_source）。
中文字型預設用 Windows／Office 內建的微軟正黑體（未安裝思源也能顯示）；要改思源用 set-deck-style --cjk-font "Noto Sans TC"。既有簡報字型顯示異常用 deck-fonts 修正。
驗收：deck-check 無 issues；build_warnings 的可能溢字逐頁處理（縮短文字優先，不靠縮字）。render_qa 為 pdf_exported 時抽看 PDF 頁面；為 skipped 時明說只做結構驗證，不得宣稱已目檢。
