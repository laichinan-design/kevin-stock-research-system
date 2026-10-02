---
name: report-validation
description: 研究流程步驟（通常由 research-router 呼叫）：交付股票研究Word、Excel與圖解，驗證資料／模型／研究結果及外掛修改。
---

# report-validation

先讀 ../../references/contract.md、../../references/deliverables.md。按模式交付必要成果，區分可用與未完成；模型不適用不阻止公司研究，缺個資不阻止監控。
模型資料與假設逐項標日期／期間／幣別。報告用官方事實、計算、來源观点、推論四種標示。長報告輸出Word，財務／來源輸出Excel，關係圖用SVG（visual-check：文字已轉外框、有來源）；簡報看 整合簡報/validation.json（deck-check 無 issues，render_qa 照實揭露）；用宿主已提供文件工具生成並檢查。
交付前跑 gaps --asof 與 readme：README 自動區塊列實際存在的成果與缺口；Drive 用 drive-sync（connector 模式：小型文字檔由宿主 Drive 連接器上傳後 drive-record，已修改檔先上傳新檔再把舊檔移到 `_舊版/`，不刪除；其餘列 待手動上傳.md 交使用者；local_sync 模式直接複製）。未上傳的檔案不得說已在 Drive。
驗證各能力而非單一總passed。改plugin時先保存副本、更新版本與CHANGELOG、重跑scripts/tests，不直接改cache。核對可打開檔案與可讀排版；未執行的驗證明列。外掛安裝與排程成功另有獨立證據。
