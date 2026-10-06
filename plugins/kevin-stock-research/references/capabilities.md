# 能力與限制
| 能力 | 本版狀態 |
| --- | --- |
| TWSE／TPEX／NYSE／NASDAQ 普通股個股設定 | 已實作格式驗證、root隔離；公司身分仍需官方查核 |
| 十種產業模板＋六種研究模式 | 已實作設定與步驟編排；研究判讀由宿主代理做 |
| 證據庫、PDF解析、財務匯入 | 已實作；程式驗證不取代人工讀表核對 |
| PDF分類（8類命名、SHA去重、來源版、硬連結、索引json/xlsx/html） | 已實作（0.3.0）；MOPS只自動判讀AI1／F04／FE4，其餘須manifest依封面指定 |
| 下載前去重（SHA／檔名／文件鍵、Drive清單） | 已實作（0.3.0）；Drive清單需宿主提供，本包不直接連Drive |
| 工程圖解（spec→SVG外框＋PNG、舊SVG轉外框、檢查） | 已實作（0.4.0）；需 fonttools／cairosvg 與一套繁中字型；示意圖內容由研究者依證據撰寫 |
| Google Drive 同步（storage.drive_folder、SHA 變動偵測、本機同步複製／連接器清單／手動清單） | 已實作（0.5.0）；本包不直接呼叫 Drive API，connector 模式由宿主連接器上傳 |
| 缺口與待下載清單、部分覆蓋、README 自動區塊、semiconductor-equipment 產業模板 | 已實作（0.5.0）；法定期限採一般業，金融業與外國發行人需手動調整 |
| datacenter-networking 產業模組（網通／交換器 ODM／JDM）、profile 的 visual_templates／deck_focus | 已實作（0.6.0）；KPI 數字仍需研究者依公司揭露填入，未揭露者標 N/A |
| osat 產業模組（封裝測試、純測試廠） | 已實作（0.7.0）；稼動率、機台數、客戶占比多數公司不逐季揭露，未揭露者標 N/A，不得推估 |
| 整合簡報（deck_style、原生圖表PPTX、結構檢查、PDF） | 已實作（0.4.0）；PDF／目檢需 LibreOffice Impress，否則只做結構驗證；工藝規格 DOCX 仍由宿主文件工具產生 |
| Excel股票映射與副本更新 | 已實作SHA256、唯一股票列、欄名、公式與單位防錯 |
| Kevin v3.7b ETF 隱含成長錨定（錨定類別、剔除記憶體（錨定與超額門檻）、超額成長Δ 上限 200、低基期旗標、景氣高峰、盈餘品質、基期EPS、情境A／B；舊雙層錨定可明示重現）／情境P/E／情境P/B／NAV | 已實作計算；ETF與大盤P/E、非經常性項目、基期調整仍需研究者提供證據 |
| TWSE盤後自動抓取 | 沿用來源adapter，需完整官方行事曆及每次來源驗證；本發行未重新做live驗收 |
| TPEX／美股盤後自動抓取 | 未實作；支援宿主查證後的標準化資料匯入，不誤用TWSE端點 |
| 批次部位 | 已實作同幣別、共用資金及產業／損失限制；無资金預留，不做FX轉換 |
| 通知outbox／狀態隔離 | 已實作SQLite交易、跨股拒絕、重試去重；實際通知靠宿主 |
| ChatGPT／Claude安裝 | 雙manifest、Claude Code用marketplace.json與安裝包；已通過claude plugin validate，帳戶端到端安裝仍需在使用者環境驗收 |

Python 3.11+；openpyxl、pypdfium2。LibreOffice或Microsoft Excel只在重算／文件渲染時需要。禁止將本機程式檢查通過說成即時數據、雲端登入、文件顯示或排程已驗證。
不同模式分開驗收：quick/full可在模型缺件時交付附缺口研究；monitor不要求個人持股；valuation須通過模型與證據；position另須帳戶完整。
