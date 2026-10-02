---
name: postclose-monitor
description: 研究流程步驟（通常由 research-router 呼叫）：已建立研究資料夾的股票盤後觀察、事件差異、每週研究更新及使用者要求的持續追蹤。
---

# postclose-monitor

先讀 ../../references/contract.md、../../references/schedule.md。live daily需官方完整calendar，API空回應不等於休市。TWSE各原始欄位日期、量／股／張單位及自營商重複項逐一核對。
其他市場若未有live adapter，使用import-market匯入宿主查证的統一快照，保留來源及資料日，不稱自動取得。1／5／20日累計提供官方交易日expected_dates；缺日回null。
用monitor --file更新security專属狀態及pending，未變安靜。weekly事件只代表需準備週報，不代表週報已寫出。完成實際通知後才ack。使用者未要求排程時僅執行當次。
