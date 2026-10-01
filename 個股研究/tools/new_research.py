#!/usr/bin/env python3
"""建立個股研究資料夾：個股研究/研究/<代號_名稱>/<YYYYMMDD>/research.json

用法：python3 new_research.py <代號> [名稱] [YYYY-MM-DD]
名稱/類別/主題若在 config/watchlist.json 中會自動帶入。
"""
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    code = sys.argv[1]
    cfg = json.loads((ROOT / "config/watchlist.json").read_text(encoding="utf-8"))
    watch = {w["code"]: w for w in cfg["watchlist"]}
    w = watch.get(code, {})
    name = sys.argv[2] if len(sys.argv) > 2 else w.get("name", "未命名")
    date = sys.argv[3] if len(sys.argv) > 3 else dt.date.today().isoformat()

    r = json.loads((ROOT / "templates/research_template.json").read_text(encoding="utf-8"))
    r["meta"].update(code=code, name=name, date=date, theme=w.get("theme", r["meta"]["theme"]))
    if w.get("category"):
        r["kevin"]["category"] = w["category"]
    r["kevin"]["h2_ramp_theme"] = bool(w.get("h2_ramp_theme", False))
    if code in cfg.get("known_W", {}):
        r["kevin"]["W"] = cfg["known_W"][code]
        r["kevin"]["W_source"] = "watchlist known_W（需以最新財報少數股東權益複核）"

    out = ROOT / "研究" / f"{code}_{name}" / date.replace("-", "")
    out.mkdir(parents=True, exist_ok=True)
    path = out / "research.json"
    if path.exists():
        sys.exit(f"已存在：{path}（不覆寫）")
    path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    if not w:
        print(f"注意：{code} 不在 watchlist，category 需手動確認（預設請用「投資組合」）")


if __name__ == "__main__":
    main()
