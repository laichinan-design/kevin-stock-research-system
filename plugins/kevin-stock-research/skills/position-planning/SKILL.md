---
name: position-planning
description: 研究流程步驟（通常由 research-router 呼叫）：以共用帳戶快照，對一檔或多檔股票計算條件式部位與資金限制。
---

# position-planning

先讀 ../../references/contract.md及examples/portfolio-batch.template.json。一次收集必要帳戶現金、資產、各股持股成本、產業曝險、損失預算、費率、買區及核心／機動比例；缺項只給條件。
只透過batch-size輸出部位，按使用者指定優先序分配同幣別的共用資金。不得將各股單獨size結果拼接。列合併後現金、產業曝險、剩餘風險與快照ID。
方案沒有資金預留，與同一快照的其他批次互斥；跨幣別目前拒絕，需另提供經查證FX換算。已確認成交用fill，各股／帳戶隔離；估計方案不能冒充持股。只提供研究，不連下單。
