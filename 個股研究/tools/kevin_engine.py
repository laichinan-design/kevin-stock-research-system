#!/usr/bin/env python3
"""個股研究計算引擎：Kevin 股價模型 → 台股雙法估值 → DCF 交叉驗證。

用法：
    python3 kevin_engine.py <research.json>            # 計算並把結果寫回 research.json 的 "valuation" 區塊
    python3 kevin_engine.py <research.json> --print    # 另外印出 markdown 摘要
    python3 kevin_engine.py --selftest                 # 用 SKILL.md 的宜鼎範例驗算

公式完全依 kevin-stock-pricing-model 與 tw-ai-dual-valuation 兩份 SKILL.md，
唯一延伸：年化因子由固定的「1-4月 ×3」一般化為「1-n月 × 12/n」（n=4 時與原版一致）。
"""
import json
import math
import sys
from pathlib import Path

BASE_PE = {  # category -> (P 常數, Q 常數)
    "投資組合": (15, 10),
    "CPO": (25, 20),
    "潛力股": (30, 25),
}


def signed_pow(x, p):
    """負成長處理：對負數取絕對值後加負號（SKILL.md Step 3）。"""
    return math.copysign(abs(x) ** p, x)


def kevin_model(k):
    missing = [f for f in ("E", "G", "H", "I", "M", "J") if not k.get(f)]
    if missing:
        raise ValueError(f"必要輸入未填（不可用猜測值補）：{missing}")
    E, H, I, M, J = k["E"], k["H"], k["I"], k["M"], k["J"]
    W = k.get("W", 1.0)
    mult = k.get("multiplier", 1.0)
    months = k.get("months", 4)
    if k["category"] not in BASE_PE:
        raise ValueError(f"category 必須是 {list(BASE_PE)}，收到 {k['category']}")
    a, c = BASE_PE[k["category"]]

    warnings = []
    if E < 1000:
        warnings.append("E < 1,000：疑似誤填為百萬元，E 單位應為千元")
    if I > 10000:
        warnings.append("I > 10,000：疑似誤填為千元，I 單位應為億元")

    annualize = 12 / months
    N = E * H * W * annualize * 10 / (I * 100000) * mult
    O = (N - J) / J
    g100 = O * 100
    P = a + signed_pow(g100, 1 / 2)
    Q = c + signed_pow(g100, 2 / 3)
    R, S = N * P, N * Q
    T = (R + S) / 2
    V = (T - M) / M
    if O < 0:
        warnings.append("預期 EPS 低於去年 EPS（O<0），本模型為成長股設計，結果僅供參考")

    return {
        "annualize_factor": annualize, "N": N, "O": O, "P": P, "Q": Q,
        "R": R, "S": S, "T": T, "V": V, "current_PE": M / N if N > 0 else None,
        "warnings": warnings,
    }


def dual_valuation(k, km):
    N, O, P, Q, M = km["N"], km["O"], km["P"], km["Q"], k["M"]
    flags = []
    # 內部一致性檢核（股本/淨利率口徑）
    q_eps = k.get("latest_q_eps")
    if q_eps is not None and N > 0 and q_eps > N:
        return {"status": "⚫", "reason": f"資料矛盾：{k.get('latest_q_label', '最新一季')} 實際 EPS {q_eps} 已超過全年外推 N={N:.2f}，股本或淨利率口徑有誤，需查證官方數字"}
    # earnings explosion 偵測
    if N <= 0:
        return {"status": "⚫", "reason": "預期 EPS ≤ 0，PE band 不適用"}
    if O > 3.0:
        flags.append(f"O={O:.0%} > 300%")
    if M / N > 150:
        flags.append(f"現價 PE={M / N:.0f} > 150")
    if flags:
        return {"status": "⚫", "reason": "earnings explosion / PE 脫離適用域（" + "、".join(flags) + "），雙法不適用，建議改用營收倍數法"}

    fwd_pe = M / N
    peg = fwd_pe / (O * 100) if O > 0 else None
    pe_band = {"Low": Q * 0.8, "Mid": (P + Q) / 2, "High": P * 1.2}
    targets = {s: N * pe for s, pe in pe_band.items()}
    upside = {s: (t - M) / M for s, t in targets.items()}
    if peg is None:
        light = "🔴"
    elif peg < 1.0:
        light = "🟢"
    elif peg <= 1.5:
        light = "🟡"
    else:
        light = "🔴"

    notes = []
    if k.get("h2_ramp_theme"):
        notes.append(f"⚠️ 模型以 1-{k.get('months', 4)}月 ×{12 / k.get('months', 4):.2f} 年化，可能低估 H2 ramp，目標價偏保守，建議對照法人 forward EPS 預估")
    if fwd_pe > pe_band["High"]:
        notes.append("Fwd PE 高於 PE band High：市場定價的成長遠超模型外推，先判斷是模型盲點還是真實高估")
    if peg is not None and peg > 1.5 and upside["Mid"] < 0:
        notes.append("強空頭訊號：PEG 偏貴且 Mid 目標價低於現價")
    if peg is not None and peg < 1.0 and upside["Mid"] > 0:
        notes.append("強多頭訊號：PEG 偏便宜且 Mid 目標價高於現價")

    return {"status": light, "fwd_PE": fwd_pe, "PEG": peg, "pe_band": pe_band,
            "targets": targets, "upside": upside, "notes": notes}


def dcf_value(d, shares_m, fcf_growth_1_5, fcf_growth_6_10, wacc, g):
    """兩階段 10 年 FCF DCF。金額單位 NT$ 百萬；回傳每股價值 (NT$)。"""
    if g >= wacc:
        raise ValueError("終值成長率 g 不可 ≥ WACC")
    fcf = d["fcf_base"]
    pv = 0.0
    for t in range(1, 11):
        fcf *= 1 + (fcf_growth_1_5 if t <= 5 else fcf_growth_6_10)
        pv += fcf / (1 + wacc) ** t
    tv = fcf * (1 + g) / (wacc - g)
    pv_tv = tv / (1 + wacc) ** 10
    ev = pv + pv_tv
    equity = ev + d.get("net_cash", 0.0)
    return {"EV": ev, "equity": equity, "per_share": equity / shares_m,
            "tv_share": pv_tv / ev if ev else None}


def dcf(research):
    d = research.get("dcf")
    if not d or d.get("fcf_base") in (None, 0):
        return None
    shares_m = research["kevin"]["I"] * 10  # 股本(億元)/面額10元 → 百萬股
    out = {"shares_m": shares_m, "scenarios": {}}
    for name, sc in d["scenarios"].items():
        r = dcf_value(d, shares_m, sc["growth_1_5"], sc["growth_6_10"], sc["wacc"], sc["g"])
        r["prob"] = sc["prob"]
        out["scenarios"][name] = r
    out["prob_weighted"] = sum(s["per_share"] * s["prob"] for s in out["scenarios"].values())
    M = research["kevin"]["M"]
    out["upside"] = (out["prob_weighted"] - M) / M
    out["tv_warning"] = any(s["tv_share"] > 0.8 for s in out["scenarios"].values())

    base = d["scenarios"]["Base"]
    waccs = [base["wacc"] + x for x in (-0.02, -0.01, 0, 0.01, 0.02)]
    gs = [base["g"] + x for x in (-0.01, -0.005, 0, 0.005, 0.01)]
    out["sensitivity"] = {
        "wacc": waccs, "g": gs,
        "grid": [[dcf_value(d, shares_m, base["growth_1_5"], base["growth_6_10"], w, g)["per_share"]
                  if g < w else None for g in gs] for w in waccs],
    }
    return out


def run(research):
    k = research["kevin"]
    km = kevin_model(k)
    dv = dual_valuation(k, km)
    dc = dcf(research)
    research["valuation"] = {"kevin": km, "dual": dv, "dcf": dc}
    return research


def fmt_pct(x):
    return "N/A" if x is None else f"{x:+.1%}"


def to_markdown(r):
    m, k, v = r["meta"], r["kevin"], r["valuation"]
    km, dv, dc = v["kevin"], v["dual"], v["dcf"]
    a, c = BASE_PE[k["category"]]
    n = k.get("months", 4)
    L = [f"## {m['name']}（{m['code']}）估值摘要　資料日 {m['date']}", ""]
    L.append(f"**Kevin 目標價 NT$ {km['T']:,.0f}，相對現價 NT$ {k['M']:,.1f} 漲幅空間 {fmt_pct(km['V'])}；"
             f"雙法綜合 {dv['status']}" + (f"；DCF 機率加權 NT$ {dc['prob_weighted']:,.0f}（{fmt_pct(dc['upside'])}）" if dc else "") + "**")
    L += ["", "### 核心輸入", "| 項目 | 數值 | 資料來源 |", "|---|---|---|",
          f"| 類別 | {k['category']}（PE {a}/{c}） | — |",
          f"| 1-{n}月累計營收 (E) | {k['E']:,.0f} 千元 | {k.get('E_source', '')} |",
          f"| 毛利率 (G) | {k['G']:.1%} | {k.get('G_source', '')} |",
          f"| 淨利率 (H) | {k['H']:.1%} | {k.get('H_source', '')} |",
          f"| 股本 (I) | {k['I']:.2f} 億 | {k.get('I_source', '')} |",
          f"| 業主淨利占比 (W) | {k.get('W', 1.0)} | {k.get('W_source', '預設')} |",
          f"| 高倍率 | ×{k.get('multiplier', 1.0)} | — |",
          f"| 目前股價 (M) | NT$ {k['M']:,.1f} | {k.get('M_source', '')} |",
          f"| 去年 EPS (J) | {k['J']:.2f} 元 | {k.get('J_source', '')} |"]
    L += ["", "### Kevin 股價模型", "| 項目 | 計算式 | 數值 |", "|---|---|---|",
          f"| 預期 EPS (N) | E×H×W×(12/{n})×10÷(I×100000) | {km['N']:.2f} 元 |",
          f"| EPS 成長率 (O) | (N−J)/J | {km['O']:.1%} |",
          f"| 預期 PE_1 (P) | {a}+(O×100)^(1/2) | {km['P']:.1f} |",
          f"| 預期 PE_2 (Q) | {c}+(O×100)^(2/3) | {km['Q']:.1f} |",
          f"| 股價 A (R) | N×P | {km['R']:,.0f} |",
          f"| 股價 B (S) | N×Q | {km['S']:,.0f} |",
          f"| **目標價 (T)** | (R+S)/2 | **NT$ {km['T']:,.0f}** |",
          f"| 漲幅空間 (V) | (T−M)/M | {fmt_pct(km['V'])} |",
          f"| 目前本益比 | M/N | {km['current_PE']:.1f} |" if km["current_PE"] else "| 目前本益比 | M/N | N/A |"]
    for w in km["warnings"]:
        L.append(f"- ⚠️ {w}")
    L += ["", "### 台股雙法估值"]
    if dv["status"] == "⚫":
        L.append(f"⚫ {dv['reason']}")
    else:
        L += ["| Fwd PE | PEG | Low | Mid | High | 綜合 |", "|---|---|---|---|---|---|",
              f"| {dv['fwd_PE']:.1f} | {dv['PEG']:.2f} | " if dv["PEG"] is not None else f"| {dv['fwd_PE']:.1f} | N/A | "]
        L[-1] += " | ".join(f"NT$ {dv['targets'][s]:,.0f}（{fmt_pct(dv['upside'][s])}）" for s in ("Low", "Mid", "High")) + f" | {dv['status']} |"
        for note in dv["notes"]:
            L.append(f"- {note}")
    if dc:
        L += ["", "### DCF 交叉驗證（NT$ 百萬 → 每股 NT$）", "| 情境 | 機率 | 每股價值 | TV 占 EV |", "|---|---|---|---|"]
        for name, s in dc["scenarios"].items():
            L.append(f"| {name} | {s['prob']:.0%} | NT$ {s['per_share']:,.0f} | {s['tv_share']:.0%} |")
        L.append(f"| **機率加權** | 100% | **NT$ {dc['prob_weighted']:,.0f}** | |")
        if dc["tv_warning"]:
            L.append("- ⚠️ 終值占 EV > 80%，DCF 對長期假設高度敏感")
    L += ["", "*本估算為 Kevin 個人模型試算，非投資建議。*"]
    return "\n".join(L)


def selftest():
    sample = {"meta": {"code": "5289", "name": "宜鼎", "date": "selftest"},
              "kevin": {"category": "投資組合", "months": 4, "E": 19853440, "G": 0.3, "H": 0.1713,
                        "I": 9.53, "M": 1760, "J": 21.72}}
    km = run(sample)["valuation"]["kevin"]
    expect = {"N": 107.07, "O": 3.93, "P": 34.82, "Q": 63.65, "T": 5272, "V": 1.995}
    ok = True
    for key, val in expect.items():
        diff = abs(km[key] - val) / abs(val)
        status = "OK" if diff < 0.005 else "FAIL"
        ok &= status == "OK"
        print(f"{key}: {km[key]:.4f} (SKILL.md {val}) {status}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if selftest() else 1)
    path = Path(sys.argv[1])
    data = run(json.loads(path.read_text(encoding="utf-8")))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md = to_markdown(data)
    path.with_name("valuation.md").write_text(md + "\n", encoding="utf-8")
    if "--print" in sys.argv:
        print(md)
