"""Research-root README: an auto block (成果入口、分類PDF、缺口、Drive) regenerated from what actually exists.
Text outside the markers is the researcher's and is never touched."""
from __future__ import annotations
import re
from pathlib import Path
from research import read, now
from library import CATEGORIES, previous_index

START='<!-- kevin:auto:start -->'
END='<!-- kevin:auto:end -->'

def link(rel,text=None): return f"[{text or Path(rel).name}]({rel.replace(' ','%20').replace('(','%28').replace(')','%29')})"
def listing(root,folder,patterns):
    d=Path(root)/folder
    return sorted({p for pat in patterns for p in d.glob(pat) if p.is_file()},key=lambda p:p.name) if d.is_dir() else []

def block(root,config):
    root=Path(root); rows=[]
    def add(what,items,status_ok,empty='待產出'):
        rows.append(f"| {what} | {'／'.join(link(p.relative_to(root).as_posix()) for p in items) if items else '—'} | {status_ok if items else empty} |")
    add('個股研究報告',listing(root,'正式成果',['*.docx','*.pdf']),'已產出')
    add('模型／估值',listing(root,'模型',['*.xlsx','valuation-*.json']),'已產出')
    add('整合簡報',listing(root,'整合簡報',['*.pptx','*.pdf']),'已產出')
    svgs=listing(root,'工程圖解',['*.svg']); live=[p for p in svgs if '<text' in p.read_text(encoding='utf-8',errors='ignore')]
    rows.append(f"| 工程圖解 | {link('工程圖解/','SVG '+str(len(svgs))+' 張') if svgs else '—'}；{link('工程圖解/PNG預覽/','PNG預覽') if (root/'工程圖解/PNG預覽').is_dir() and any((root/'工程圖解/PNG預覽').glob('*.png')) else 'PNG 待產'} | "
                f"{('已產出（文字已轉外框）' if not live else f'{len(live)} 張仍為活字，需 visual-outline') if svgs else '待產出'} |")
    add('工藝與工程規格',listing(root,'工程圖解',['*工藝*.docx','*工藝*.pdf']),'已產出')
    idx=previous_index(root); counts={c:sum(r.get('category')==c for r in idx) for c in CATEGORIES}
    rows.append(f"| 分類PDF | {link('分類PDF/PDF分類目錄.html','分類目錄') if (root/'分類PDF/PDF分類目錄.html').exists() else '—'} | {sum(counts.values())} 份 |")
    gaps=read(root/'缺口清單.json') if (root/'缺口清單.json').exists() else {'gaps':[],'partial':[]}
    todo=link('待下載清單.md') if (root/'待下載清單.md').exists() else ''
    rows.append(f"| 缺口 | {link('缺口清單.json')}{'／'+todo if todo else ''} | {len(gaps.get('gaps',[]))} 項缺口、{len(gaps.get('partial',[]))} 份部分覆蓋 |")
    out=[START,'',f"_自動區塊，產生於 {now()}；改內容請改檔案後重跑 `readme`，此區塊外的文字不會被覆寫。_",'','## 成果入口','','| 內容 | 檔案 | 狀態 |','|---|---|---|']+rows
    out+=['','## 分類PDF 現況','','| 類別 | 份數 |','|---|---|']+[f'| {c} | {n} |' for c,n in counts.items()]
    st=config.get('storage')
    if st:
        from storage import plan
        p=plan(root,config); manual=[c for c in p['changed'] if c.get('via')=='manual']
        out+=['','## Google Drive','',f"- 資料夾：`{p['drive_folder']}`（模式：{p['mode']}；上次同步：{p.get('last_sync') or '尚未'}）",
              f"- 未同步：{len(p['changed'])} 檔" + (f"，其中 {len(manual)} 檔需手動上傳，見 {link('待手動上傳.md')}" if manual and (root/'待手動上傳.md').exists() else '')]
    out+=['',END]
    return '\n'.join(out)

def write(root,config):
    root=Path(root); path=root/'README.md'; auto=block(root,config)
    if path.exists():
        text=path.read_text(encoding='utf-8')
        if START in text and END in text:
            text=re.sub(re.escape(START)+r'.*?'+re.escape(END),lambda m:auto,text,count=1,flags=re.S)
        else:
            lines=text.split('\n',1); text=lines[0]+'\n\n'+auto+'\n'+(lines[1] if len(lines)>1 else '')
    else:
        text=f"# {config['name']} {config['security']} 研究\n\n{auto}\n\n## 接續原則\n- 下載前先 dedupe-check；已持有的年報、財報不重抓。\n- 原始文件以 SHA256 命名、不改寫；分類PDF 為硬連結入口。\n\n非投資建議。\n"
    path.write_text(text,encoding='utf-8')
    return {'file':str(path),'auto_block_lines':auto.count('\n')+1}
