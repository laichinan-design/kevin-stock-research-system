# Kevin 投資研究系統 — Claude 工作規範

使用者：Kevin（台中，台股/半導體供應鏈投資研究者）。一律繁體中文，技術詞（EPS、capex、P/E、CAGR、CPO…）保留英文。結論先行、表格優先、幣別標 NT$。

## 個股研究流程（觸發語：「個股研究 <代號>」「跑個股研究」「研究 <代號>」）

收到觸發語就跑完整 8 步，不要縮減、不要先問「要做什麼」。多檔時逐檔建資料夾，最後加一張跨股比較表（依 Kevin V 由高到低）。

| 步驟 | 內容 | 對應 skill（規則以 skill 為準） | 寫入 research.json |
|---|---|---|---|
| 0 | 開案：`python3 個股研究/tools/new_research.py <代號>` | — | meta、category、W |
| 1 | 資料蒐集（見下方鐵則） | kevin-stock-pricing-model | `kevin.*` 與各 `_source` |
| 2 | Kevin 股價模型 | kevin-stock-pricing-model | 引擎計算 |
| 3 | 台股雙法估值（PEG + PE band、⚫ 偵測） | tw-ai-dual-valuation | 引擎計算 |
| 4 | 產業鏈定位、chokepoint、價值遷移 | invest-industry-map | `industry_map` |
| 5 | Moat + Five Forces + 同業比較 | invest-competitor-analysis | `competition` |
| 6 | DCF 三情境交叉驗證 + 5×5 敏感度 | invest-dcf-valuation | `dcf` |
| 7 | Bear case 空方紅隊（0-10 分、thesis-killers） | invest-bear-case | `bear` |
| 8 | 綜合結論、訊號框、失效條件、產出檔案 | — | `conclusion`、`sources` |

產出：`bash 個股研究/tools/run_pipeline.sh 個股研究/研究/<代號_名稱>/<YYYYMMDD>/research.json`
→ `valuation.md`（對話摘要）、`*_估值模型_*.xlsx`（連動公式）、`*_個股研究報告_*.docx`。
完成後：更新 `個股研究/研究索引.md`、commit + push，把 .docx/.xlsx 傳給使用者，對話中貼結論與關鍵表格。

## 資料鐵則（違反即停）

1. **G 毛利率 / H 淨利率**：只能取最新一期已公告季報（→半年報→年報），用「毛利 / 營收」「歸屬母公司淨利 / 營收」原始數字自己算。禁止法人預估、媒體推估、外推、上期沿用。
2. **I 股本**：只能取 MOPS「普通股股本」或券商明列資本額。**嚴禁**以淨利÷EPS 或市值÷股價反推；抓不到就停下來問。
3. **E 累計營收**：單位千元，取最新已公告月份的 1-n 月累計，`months=n`（年化因子 12/n；n=4 即原版「1-4月×3」）。
4. **M 現價**：必須即時，記錄時間戳；抓不到就問，不用過期價。
5. **一致性檢核**：填 `latest_q_eps`。最新一季實際 EPS > N → ⚫ 資料矛盾，不輸出目標價。
6. **W**：預設 1.0；有重要少數股東權益者（奇鋐≈0.916、鼎炫≈0.775）調整並註明。
7. 抓不到的輔助數字標 N/A，不憑記憶填補；有假設就明講假設前提。
8. 散熱 / CPO / 先進封裝設備（`h2_ramp_theme=true`）一律加註年化可能低估 H2 ramp。

資料來源優先序：公開資訊觀測站 MOPS → Goodinfo → 鉅亨 / MoneyDJ → 公司 IR；即時股價：TWSE/TPEx、wantgoo、Yahoo。

## 免責

報告與對話結尾附一次「非投資建議」，不重複警示。

## 其他專案

- `三電系統開發/`：達方 E-mobility 三電系統 BOM 與訂閱制研究（非個股流程）。
