# Kevin 股票研究系統：工作規則

## 研究結果存放位置（Google Drive）

個股研究、資料複核、估值等產出，一律存到 Google Drive，不要只放在對話或本 repo。

- 根目錄：`投資組合-台股`（folder id `1pTeqf8ZPtidGCKkHbgk67QGqQ97xx6Kg`）
- 個股子資料夾命名：`{公司簡稱}{代碼}`，不留空白，例如 `智邦2345`、`松川精密7788`、`新盛力4931`
  - 有少數既有資料夾的命名不同（例如 `AES-KY 6781`），沿用既有資料夾，不要重建
- 適用範圍：最新一份 `投資組合-台股/投資組合_YYYY_MM_DD_updated.xlsx` 裡「投資組合」「CPO概念」「潛力股」三張表列出的股票
  - 先搜尋 `parentId = '1pTeqf8ZPtidGCKkHbgk67QGqQ97xx6Kg'` 找既有的個股資料夾；沒有才建立
  - 不在清單內的股票：先問 Kevin 要存哪裡
- 檔名：`{代碼}_{公司簡稱}_{主題}_{YYYYMMDD}.xlsx`（或 `.docx`），例如 `2345_智邦_官方資料複核_20261001.xlsx`
- 上傳時保留原始格式（`disableConversionToGoogleType: true`），不要轉成 Google 格式

## 已知資料夾 ID

| 股票 | 資料夾 | ID |
|---|---|---|
| 智邦 2345 | `投資組合-台股/智邦2345` | `1DsnUljDO0kaNToZAVOjCAWu8SJYvz-GQ` |

## 官方資料來源

- 雲端環境的網路政策會擋掉 MOPS／TWSE 網域（`mops.twse.com.tw`、`mopsov.twse.com.tw`、`openapi.twse.com.tw`、`www.twse.com.tw`）
- 個股資料夾通常已經放有 MOPS 下載的財報 PDF（`YYYYQQ_代碼_AI1_*.pdf` 是合併財報），請優先讀這份做官方複核
- 業主淨利占比用「歸母淨利 ÷ 本期淨利（合併）」計算；非控制權益為負數時，占比會大於 100%
