---
name: document-organizer
description: 研究流程步驟（通常由 research-router 呼叫）：整理研究資料夾內的股票研究文件、PDF頁碼、財務事實、去重與修訂版本。
---

# document-organizer

先讀 ../../references/contract.md。extract輸出實體PDF頁碼；另記印刷頁、表名和OCR抽核。facts用examples/fact.template.json建立，每筆包含available_at、revision_basis與locator，經facts指令驗證。
unit正規化為profiles/metrics.json的基準單位；股票數及EPS單位分開。只有流量白名單可累計轉單季，EPS與存量不相減。不同重編系列不得相減。
同bytes多來源可共用檔案但保留來源關係。全文閱讀紀錄另存，full不代表讀完。使用者提供的缺漏資料不得用推測填補。
PDF分類：先跑 classify-pdfs（dry-run）檢視 actions／unclassified／conflicts，確認後加 --apply。8類：01_年報、02_年度財報、03_季報、04_法說會資料、05_技術簡報、06_券商研究、07_產業資料、08_股東會與公司治理。年報label用會計年度；全年財報歸02不得標Q4；Q2／Q3標「含累計」；法說會、券商、股東會用YYYY-MM-DD；外部研究為發布機構_日期_主題_語言。同SHA只留一份；同名不同SHA全部加_來源版SHA前8碼。MOPS代碼只認AI1／F04／FE4，其他來源（公司IR、券商、產業）以manifest指定category/label/title/publisher，判讀依封面與標題，不從檔名猜。分類檔為硬連結，不改寫、不刪原始文件；05技術簡報不收法說會或產業特刊。
