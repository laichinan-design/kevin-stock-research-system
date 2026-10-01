---
name: document-organizer
description: 研究流程步驟（通常由 research-router 呼叫）：整理研究資料夾內的股票研究文件、PDF頁碼、財務事實、去重與修訂版本。
---

# document-organizer

先讀 ../../references/contract.md。extract輸出實體PDF頁碼；另記印刷頁、表名和OCR抽核。facts用examples/fact.template.json建立，每筆包含available_at、revision_basis與locator，經facts指令驗證。
unit正規化為profiles/metrics.json的基準單位；股票數及EPS單位分開。只有流量白名單可累計轉單季，EPS與存量不相減。不同重編系列不得相減。
同bytes多來源可共用檔案但保留來源關係。全文閱讀紀錄另存，full不代表讀完。使用者提供的缺漏資料不得用推測填補。
