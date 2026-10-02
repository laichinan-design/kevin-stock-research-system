# Kevin 股票研究 0.5.0｜雙平台安裝

這是一份共用核心、可分別安裝於 ChatGPT 桌面 Work／Codex 及 Claude 的外掛包。先把總ZIP解壓到固定資料夾，保留隱藏目錄。不是把總ZIP丟進一般聊天就會自動安裝。

## ChatGPT 桌面 Work／Codex
官方文件確認：Work／Codex 的本機 marketplace 可提供自訂外掛；一般聊天上傳附件不等於安裝。功能及組織權限仍依實際帳戶。

方法A（Windows有Codex CLI）：在解壓後資料夾開PowerShell執行：
```powershell
.\install-openai.ps1
```
可先用 `.\install-openai.ps1 -DryRun` 查看目標，不更動設定。若PowerShell限制執行腳本，可手動執行以下兩個CLI命令，不需要修改系統政策：
```text
codex plugin marketplace add "完整解壓資料夾路徑"
codex plugin add kevin-stock-research@kevin-research-bundle
```
先註冊marketplace成功，再安裝；不要省略第一步。完成後重新開啟桌面app，在Plugins中確認0.5.0，開新聊天使用。

方法B（Work／Codex有本機專案、沒有CLI）：把解壓後資料夾開為本機專案／工作目錄，重新啟動app，在Plugins Directory選擇kevin-research-bundle來源並安裝。若該版本未顯示本機來源，把plugins/kevin-stock-research交給內建plugin-creator，要求註冊到個人marketplace；不要手改cache。

已安裝0.1.0者：這個發行包使用獨立marketplace名稱。新版本確認可載入後，在Plugins停用舊personal來源的同名外掛，避免重複技能。既有研究及排程不因安裝自動遷移；先dry-run檢查再切換。
已安裝0.2.x–0.4.0者：以本版資料夾重新註冊後更新，確認顯示0.5.0；舊研究資料夾執行 set-storage 設定 Drive 資料夾、readme 產生自動區塊；既有研究資料夾開啟時自動補建分類PDF、工程圖解、整合簡報資料夾，不動既有檔案。舊版產生的工程圖 SVG 若文字不顯示，執行 visual-outline 轉外框。
已安裝0.2.0者：0.2.0的Kevin估值請求若含multiplier≠1或base_pe_low／base_pe_high會被拒絕，依references/kevin-model.md最後一節改寫。

## Claude
方法A（Claude App／帳戶）：在 Customize → Plugins 使用上傳自訂plugin的入口，選擇解壓後 `kevin-stock-research.plugin`，完成確認後開新對話。若上傳介面不接受此副檔名，改名為.zip再試（內容是標準zip）。上傳到帳戶的plugin會同步到Claude Code。Cowork可先開Cowork頁再進Customize。選擇的是內層.plugin檔，不是總ZIP。
方法B（Claude Code本機marketplace）：本包根目錄附 `.claude-plugin/marketplace.json`，已通過 `claude plugin validate`。建議先把解壓資料夾放在不含中文與空格的本機路徑，再執行：
```text
claude plugin marketplace add "完整解壓資料夾路徑"
claude plugin install kevin-stock-research@kevin-research-bundle
```
只想本次試用：`claude --plugin-dir "完整解壓資料夾/plugins/kevin-stock-research"`，不算永久安裝。
方法A與B擇一，避免同一組技能出現兩份。帳戶／組織可能限制自訂外掛。若宿主没有檔案或Python執行能力，仍可讀取研究指引，但不能執行本機計算與檔案更新。每股研究資料夾含SQLite資料庫，建議放本機磁碟，不放雲端同步資料夾。

## 安裝後第一句
「使用Kevin股票研究，先列出版本與可用能力，然後完整研究TWSE:2330；依官方資料確認股票身分，建立獨立研究資料夾，沒有模型就先交付研究與缺口。」
其他股票只要改市場、代號、公司名與適用產業。不可照搬範例估值、模型列號或前一檔股票的來源。

## 本版包含
- 10項skills：研究總入口＋原七個研究模組＋工程圖解（engineering-visuals）＋整合簡報（integrated-deck）。
- 8種產業模板、6種任務模式、四種估值計算方法。
- 個股資料隔離、可追溯證據庫、財務期間與單位檢核。
- Excel股票鍵／欄位／指紋檢查、只更新副本。
- 共用資金的批次部位試算、獨立監控狀態與去重。
- 測試、空白設定範本、CLI文件與舊版dry-run遷移。
- 0.2.1：Kevin雙層錨定（三類錨定比例、盈餘品質與本業淨利率、基期EPS調整、情境A／B、溢價只乘模型價）。
- 0.3.0：分類PDF（8類命名、SHA256去重、來源版、硬連結、索引json/xlsx/html）、下載前去重（已持有的年報／財報不重抓）、研究資料夾新結構。
- 0.5.0：Google Drive 同步（storage.drive_folder；本機 Google Drive 桌面版直接複製，雲端則產生連接器／手動上傳清單）、缺口與待下載清單（法定文件期限推算、部分覆蓋）、README 自動區塊、半導體設備與自動化產業模板。
- 0.4.0：工程圖解 spec→SVG（文字轉外框，任何檢視器都能顯示）＋PNG預覽；整合簡報 deck_style（10配色×3字型）、原生可編輯圖表PPTX、溢字／0軸／來源檢查、PDF匯出。

## 實際範圍
TPEX與美股可以使用研究流程及經核對的資料匯入；本版未實作其自動盤後抓取介面。TWSE沿用既有介面，但本次發行未重做live資料驗收。部位方案不預留現金；同一帳戶快照的不同批次互斥。DCF等方法只有研究指引、没有計算器。安裝不建立排程、不連券商、不含私人資料。

依賴：Python 3.11+，openpyxl、pypdfium2；工程圖解與簡報另需 fonttools、brotli、cairosvg、python-pptx、Pillow 與一套繁中字型（微軟正黑體即可）；Excel重算與簡報PDF另需LibreOffice或Office。使用宿主已有runtime優先，必要時在独立venv安裝requirements.txt。程式測試及格式驗證結果见RELEASE-VALIDATION.json；兩平台登入帳戶實機安裝需在使用者環境完成，本包不宣稱已完成該步。

## 包內檔案
- `plugins/kevin-stock-research/`：共用完整外掛原始碼，含OpenAI與Claude manifests。
- `kevin-stock-research.plugin`：同一份內容的Claude上傳安裝檔。
- `.agents/plugins/marketplace.json`：ChatGPT／Codex用的本機catalog。
- `.claude-plugin/marketplace.json`：Claude Code用的本機marketplace（0.2.1新增）。
- `install-openai.ps1`：先註冊來源再安裝的Windows腳本。
- `FILE-HASHES.json`、`RELEASE-VALIDATION.json`：完整性與驗收結果。

## 官方依據（2026-10-01查閱，0.4.0未重查）
- [OpenAI：Package your plugin](https://developers.openai.com/plugins/build/plugins)
- [Claude：Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude)

非投資建議。
