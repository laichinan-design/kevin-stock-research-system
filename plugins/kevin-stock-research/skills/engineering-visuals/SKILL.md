---
name: engineering-visuals
description: 研究流程步驟（通常由 research-router 呼叫）：為研究中的公司產出產品工程圖解（SVG＋PNG預覽，文字轉外框保證任何檢視器可顯示）與《主要產品_工藝與工程規格》文件；也用於修正舊 SVG 文字無法顯示。
---

# engineering-visuals

先讀 ../../references/contract.md、../../references/cli.md 的「工程圖解」節。只畫有證據的內容；每張圖頁腳「來源：文件＋頁碼／網址」，非公司原圖或實物照片一律標「示意圖」（spec 預設 illustrative=true）。
選圖先讀 config.industry 對應 profiles/industries JSON 的 visual_templates（有就照它的圖組與順序）；沒有時依產業通則：PCB／載板／CPO／矽光子／封裝用「層疊剖面＋工序流程＋關鍵精度」；散熱用「熱路架構＋製程難點」；設備／自動化用「系統架構＋作業流程＋導入模式」；網通／交換器用「產品架構剖面＋網路拓撲落點＋速率世代＋ODM／JDM 流程」；共通加「價值鏈位置」「產品演進」。5–8 張，編號 01–NN。
每張寫 diagram spec（JSON：id、name、title、subtitle、source、elements: box／arrow／lane／line／text），用 visual-build 產生：工程圖解/NN_名稱.svg（文字已轉外框）、工程圖解/原始碼/NN_名稱.json（可編修母檔）、工程圖解/PNG預覽/NN_名稱.png。改圖改 JSON 重跑，不手改 SVG。
字型：自動找思源黑體／Noto Sans TC → 微軟正黑體 → 蘋方 → fontconfig，另加 Segoe UI／Arial／DejaVu 補 μ、Ω、±；可用 --font-dir 或 KEVIN_FONT_DIR 指定。缺字直接報錯，改字或換字型，不得留豆腐字。舊 SVG 用 visual-outline 轉外框並重產 PNG，visual-check 驗收（無 <text> 活字、有 viewBox、有來源）。
工藝與工程規格 DOCX（用宿主 docx 工具）：產品別列 材料、製程步驟、關鍵尺寸／公差、良率或檢測關口、設備、客戶應用；無公開數據填「N/A（未揭露）」，推估欄位標「研究推論」並寫依據，不得編造規格。嵌入 PNG預覽，表格附來源頁碼。照片只用有授權或公司公開素材，另列圖片來源清單。
簡報引用 PNG預覽（不是 SVG）。完成後在 README 成果入口更新狀態。
