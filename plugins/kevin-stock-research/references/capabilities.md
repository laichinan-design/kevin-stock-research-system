# 能力與限制
| 能力 | 本版狀態 |
| --- | --- |
| TWSE／TPEX／NYSE／NASDAQ 普通股個股設定 | 已實作格式驗證、root隔離；公司身分仍需官方查核 |
| 七種產業模板＋六種研究模式 | 已實作設定與步驟編排；研究判讀由宿主代理做 |
| 證據庫、PDF解析、財務匯入 | 已實作；程式驗證不取代人工讀表核對 |
| Excel股票映射與副本更新 | 已實作SHA256、唯一股票列、欄名、公式與單位防錯 |
| Kevin雙層錨定（錨定類別、盈餘品質、基期EPS、情境A／B）／情境P/E／情境P/B／NAV | 已實作計算；ETF與大盤P/E、非經常性項目、基期調整仍需研究者提供證據 |
| TWSE盤後自動抓取 | 沿用來源adapter，需完整官方行事曆及每次來源驗證；本發行未重新做live驗收 |
| TPEX／美股盤後自動抓取 | 未實作；支援宿主查證後的標準化資料匯入，不誤用TWSE端點 |
| 批次部位 | 已實作同幣別、共用資金及產業／損失限制；無资金預留，不做FX轉換 |
| 通知outbox／狀態隔離 | 已實作SQLite交易、跨股拒絕、重試去重；實際通知靠宿主 |
| ChatGPT／Claude安裝 | 雙manifest、Claude Code用marketplace.json與安裝包；已通過claude plugin validate，帳戶端到端安裝仍需在使用者環境驗收 |

Python 3.11+；openpyxl、pypdfium2。LibreOffice或Microsoft Excel只在重算／文件渲染時需要。禁止將本機程式檢查通過說成即時數據、雲端登入、文件顯示或排程已驗證。
不同模式分開驗收：quick/full可在模型缺件時交付附缺口研究；monitor不要求個人持股；valuation須通過模型與證據；position另須帳戶完整。
