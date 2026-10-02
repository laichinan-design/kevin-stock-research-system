# kevin-stock-research plugin 修改建議（0.2.2 → 0.3.0）

> 依據：《健策3653研究》資料夾結構 + 本次竹陞 6739 補做工程圖解／產品工藝／整合簡報／分類PDF 的實作經驗（2026-10-02）。

## 核心結論

目前 plugin 只負責「證據 → 數據 → 模型 → 報告」，**缺三塊：文件分類層、視覺化產出層（工程圖解＋簡報）、下載前去重**。建議用 1 個新指令 + 2 個新 skill + 1 個 config 欄位補齊，其餘是既有 skill 的擴充。

> **實作狀態（2026-10-02）**：全部 11 項已實作。P0（1–3）於 0.3.0；P1（4–7，含 engineering-visuals、integrated-deck、router、deck_style）於 0.4.0；`storage.drive_folder` 與 P2（8–11：gaps／coverage-set、semiconductor-equipment、README 自動區塊、tools/build_release.py）於 0.5.0。

## 修改總表（依優先序）

| # | 優先 | 範圍 | 修改內容 | 主要檔案 |
|---|---|---|---|---|
| 1 | P0 | 資料夾 layout | init 增建 `分類PDF/01–08`、`工程圖解/{PNG預覽,實物設備詳解版,工藝精度圖例增補版}`、`整合簡報/`；根目錄產 `README.md`、`缺口清單.json` | `scripts/research.py:40`、`references/deliverables.md` |
| 2 | P0 | document-organizer | 新增 `classify-pdfs` 指令：8 類分類、命名規則、SHA256 去重、硬連結、索引三件組 | `skills/document-organizer/SKILL.md`、`scripts/workflow.py` |
| 3 | P0 | data-acquisition | 下載前去重：MOPS 檔名代碼表 + 既有檔 original_filename / SHA256 比對，已存在年報不重抓 | `skills/data-acquisition/SKILL.md`、`scripts/mops.py` |
| 4 | P1 | 新 skill `engineering-visuals` | SVG 母檔 + PNG 預覽 + 《產品工藝與工程規格.docx》 | 新增 `skills/engineering-visuals/` |
| 5 | P1 | 新 skill `integrated-deck` | 標準大綱、串接 ppt-style-picker、原生圖表、pptx＋pdf | 新增 `skills/integrated-deck/` |
| 6 | P1 | research-router | full 模式流程加入 classify → visuals → deck | `skills/research-router/SKILL.md`、`workflow.py` MODES |
| 7 | P1 | config | 新增 `storage.drive_folder`、`deck_style` | `config.json` schema、`references/contract.md` |
| 8 | P2 | 雲端／離線感知 | 被擋來源標記、產 `待下載清單`、記錄部分覆蓋（例：年報 p.1–76） | `report-validation`、`缺口清單.json` |
| 9 | P2 | 產業 profile | 新增 `semiconductor-equipment`（設備／自動化）子型 | `profiles/industries/` |
| 10 | P2 | README 模板 | 仿健策「成果入口表＋接續原則＋限制」 | `references/deliverables.md` |
| 11 | P2 | 工程流程 | 版本 0.3.0、CHANGELOG、單元測試、Drive release 同步 | `plugin.json`×3、`CHANGELOG.md`、`scripts/test_*.py` |

---

## 1. Layout（P0）

`research.py:40` 改為：

```python
LAYOUT = (
  '原始文件', '文件文字', '財務數據', '模型', '盤後紀錄', '正式成果',
  '分類PDF/01_年報', '分類PDF/02_年度財報', '分類PDF/03_季報', '分類PDF/04_法說會資料',
  '分類PDF/05_技術簡報', '分類PDF/06_券商研究', '分類PDF/07_產業資料', '分類PDF/08_股東會與公司治理',
  '工程圖解/PNG預覽', '工程圖解/實物設備詳解版', '工程圖解/工藝精度圖例增補版',
  '整合簡報',
)
for f in LAYOUT: (self.root/f).mkdir(parents=True, exist_ok=True)
```

- 空類別自動放 `目前無檔案.txt`（健策做法），避免 Drive 同步時資料夾消失。
- `test_research.py` 加一條 layout 斷言。

## 2. `classify-pdfs`（P0）

**命名規則**（寫進 SKILL.md 並由程式強制）：

| 類別 | 規則 | 例 |
|---|---|---|
| 年報 | 依**會計年度**，不是股東會日期 | 2026-05 股東會年報 → `竹陞_6739_2025_年報_中文.pdf` |
| 年度財報 | 全年報告**不得**標成 Q4 | MOPS `202504_AI1` → `_2025_年度合併財報_` |
| 季報 | Q2／Q3 標示「含累計」，不可把累計數當單季 | `_2025Q2_合併季報_含上半年累計_` |
| 法說會／股東會 | 依**會議日期** | `_20260909_法說會簡報_` |
| 券商／產業 | `發布機構_日期_主題_語言.pdf` | `元大_20260915_竹陞首評_中文.pdf` |

**去重**：同 SHA256 只留一份；同標題不同 SHA → 加 `_來源版A/B` 短碼並在索引註記。分類檔用**硬連結**（同磁碟）或 Drive shortcut，不複製。

**輸出三件組**：`PDF分類索引.json/.xlsx`、`PDF分類目錄.html`、`整理說明.md`。每筆欄位：`category, period, filename, original_filename, sha256, pages, drive_file_id, source_url, note`。

## 3. 下載前去重（P0）

`mops.py` 加代碼表，下載前先查本機 `原始文件/`、`分類PDF/` 與 Drive 既有檔：

```python
MOPS_CODES = {'AI1': '合併財報(YYYYQQ; QQ=04 為全年)', 'F04': '股東會年報', 'F01': '議事手冊', ...}
def already_have(orig_name, sha=None):
    return index.find(original_filename=orig_name) or (sha and index.find(sha256=sha))
```

- 比對鍵：`original_filename`（MOPS 檔名含代碼與年月）優先，下載後再以 SHA256 確認。
- 本次竹陞即依此**沒有重抓 2025 年報**，直接把既有 5 份 PDF 搬移改名。

## 4. 新 skill：engineering-visuals（P1）

- 產物：`工程圖解/NN_主題.svg`（母檔）＋ `PNG預覽/NN_主題.png`（cairosvg）＋ `{公司}主要產品_工藝與工程規格.docx`。
- 必備圖：系統架構、核心製程／流程、產品演進、價值鏈位置、導入與商業模式。
- 規則：
  - 每張圖頁腳標**資料來源與頁碼**；非實物照片一律標「示意圖」。
  - 規格表無公開數據填 `N/A（未揭露）`，推論欄位標 `研究推論`，不得編造。
  - CJK 字型：SVG 寫 `Noto Sans TC, Microsoft JhengHei`，render 時替換為環境可用字型（避免 tofu）。
- 依產業選模板：PCB／CPO／封裝用「層疊剖面＋工序」，設備／自動化用「系統架構＋流程」。

## 5. 新 skill：integrated-deck（P1）

- 先呼叫 `ppt-style-picker`，選擇寫入 `config.json` 的 `deck_style`（例 `{"palette":"07","font":"C"}`），之後 refresh 沿用不再詢問。
- 標準大綱（20–28 頁）：封面與結論 → 公司與產品 → 工程圖解 → 供應鏈與競爭 → 財務與估值（Kevin 模型）→ 風險與追蹤。
- 數字圖表用 pptxgenjs **原生 chart**（可編輯），工程圖引用 `PNG預覽/`。
- 輸出 pptx＋pdf；`validation.json` 記錄 render QA 是否執行（環境無 LibreOffice 時標 `render_qa: skipped`，不得宣稱已目檢）。

## 6. research-router full 流程（P1）

```
data-acquisition(去重) → document-organizer(+classify-pdfs) → fundamental-research
→ engineering-visuals → kevin-model → integrated-deck → report-validation
```

- `quick` / `monitor` 不跑 visuals 與 deck；`refresh` 只重產數字頁。

## 7. config 新欄位（P1）

```json
"storage": {"drive_folder": "投資組合-台股/{公司}{代碼}/{公司}{代碼}研究", "binary_upload": "local_sync"},
"deck_style": {"palette": "07", "font": "C"}
```

- 二進位檔（pptx/docx/png/xlsx）走本機 Google Drive 同步資料夾；雲端環境只能上傳文字格式（md/html/json/svg/Google Doc），README 需列「待手動上傳」清單。
- 注意：健策在 Drive 上的 `整合簡報/`、`工程圖解/` 子資料夾、`正式成果/`、`模型/` 目前是空的——pptx/docx 當初沒同步上去，建議先補傳。

## 8. 雲端／離線感知（P2）

- `report-validation` 新增檢查：被擋來源（MOPS、公司官網）→ 產 `待下載清單.md`（含 MOPS 代碼與期別），不得用二手資料靜默替代。
- 部分覆蓋要記錄，例如 `{"doc":"2025年報","pages_covered":"1-76","missing":"77-101"}`。

## 9. 產業 profile：semiconductor-equipment（P2）

KPI：裝機量／滲透率、相容機型數、劇本（recipe）數、客戶集中度、驗收認列時點與在製品水位、毛利率結構（軟體 vs 硬體）。竹陞即屬此類，現行 `semiconductor` profile 的「稼動率、製程節點」不適用。

## 10. README 模板（P2）

仿健策：`成果入口`表（檔案、用途、狀態）→ `分類PDF 現況`（各類數量）→ `接續原則`（下次 refresh 從哪接）→ `限制與缺口`。

## 11. 工程流程（P2）

- 三個 `plugin.json` 同步改 0.3.0，CHANGELOG 列上述項目。
- 新測試：命名規則（年報 FY、年度財報非 Q4、季報累計標記）、SHA 去重、layout、`already_have()`。
- `validate_package.py` 加檢查新 skill 的 SKILL.md frontmatter。

---
非投資建議。
