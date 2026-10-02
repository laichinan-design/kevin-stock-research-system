"""Gap list for offline/cloud runs: statutory filings that should exist by asof but are not held, blocked sources,
and partially read documents. Writes 缺口清單.json (manual entries preserved) and 待下載清單.md for a local run."""
from __future__ import annotations
from datetime import date
from pathlib import Path
from research import dump, read, now
from library import QUARTER_TITLE, doc_key, key_from_name, original_name, previous_index

GAPS='缺口清單.json'
TODO='待下載清單.md'
# Taiwan listed companies (一般業) statutory deadlines; financial/insurance/foreign issuers differ, and 年報 depends on the AGM date.
DEADLINES={1:'05-15',2:'08-14',3:'11-14'}
ANNUAL_FS='03-31'; ANNUAL_REPORT='06-30'

def expected(asof,ticker,years=2):
    asof=date.fromisoformat(asof); out=[]
    for fy in range(asof.year-years,asof.year+1):
        due=date.fromisoformat(f'{fy+1}-{ANNUAL_FS}')
        if due<=asof: out.append({'category':'02_年度財報','label':str(fy),'title':'年度合併財報','code':'AI1','mops_kind':'A','mops_filename':f'{fy}04_{ticker}_AI1.pdf','due':due.isoformat()})
        due=date.fromisoformat(f'{fy+1}-{ANNUAL_REPORT}')
        if due<=asof: out.append({'category':'01_年報','label':str(fy),'title':'年報','code':'F04','mops_kind':'F','mops_filename':f'{fy}_{ticker}_{{股東會日期}}F04.pdf','due':due.isoformat(),'due_note':'依股東會日期，約 5–6 月'})
        for q,md in DEADLINES.items():
            due=date.fromisoformat(f'{fy}-{md}')
            if due<=asof: out.append({'category':'03_季報','label':f'{fy}Q{q}','title':QUARTER_TITLE[q],'code':'AI1','mops_kind':'A','mops_filename':f'{fy}{q:02d}_{ticker}_AI1.pdf','due':due.isoformat()})
    for e in out: e['language']='中文'; e['mops_roc_year']=int(e['label'][:4])-1911
    return out

def held_keys(store,config):
    ticker=str(config['ticker']); keys=set()
    for r in previous_index(store.root):
        k=doc_key(r.get('category'),str(r.get('label') or r.get('period') or ''),r.get('language') or '中文',r.get('title') or '')
        if k: keys.add(k)
        for n in [r.get('name'),r.get('filename'),r.get('original_filename')]+list(r.get('original_filenames',[]))+[original_name({'url':u}) for u in r.get('source_urls',[])]:
            k=key_from_name(n,ticker) if n else None
            if k: keys.add(k)
    for p in (store.root/'分類PDF').glob('*/*.pdf'):
        k=key_from_name(p.name,ticker)
        if k: keys.add(k)
    for r in store.evidence():
        if r['status']=='full':
            k=key_from_name(original_name(r),ticker)
            if k: keys.add(k)
    return keys

def load(root,security):
    p=Path(root)/GAPS
    data=read(p) if p.exists() else {}
    return {'security':data.get('security',security),'asof':data.get('asof'),'gaps':list(data.get('gaps',[])),'partial':list(data.get('partial',[]))}

def coverage_set(root,config,doc,pages_covered,total_pages=None,missing=None,note=''):
    data=load(root,config['security'])
    entry={'doc':doc,'pages_covered':pages_covered,'total_pages':total_pages,'missing':missing,'note':note,'updated':now()}
    data['partial']=[x for x in data['partial'] if x.get('doc')!=doc]+[entry]
    dump(Path(root)/GAPS,data); return entry

def refresh(store,config,asof,years=2):
    root=store.root; data=load(root,config['security']); ticker=str(config['ticker'])
    manual=[g for g in data['gaps'] if not g.get('auto')]
    held=held_keys(store,config); auto=[]
    for e in expected(asof,ticker,years):
        if doc_key(e['category'],e['label'],e['language'],e['title']) in held: continue
        auto.append({'id':f"mops-{e['code']}-{e['label']}",'auto':True,'kind':'statutory_missing',
                     'item':f"{e['label']} {e['title']}",'category':e['category'],'need':f"MOPS {e['code']}（discover kind={e['mops_kind']}, ROC {e['mops_roc_year']}"+(f" 或 {e['mops_roc_year']+1}，依股東會年度" if e['code']=='F04' else '')+"）",
                     'mops_filename':e['mops_filename'],'due':e['due'],'impact':'法定文件未持有'})
    for r in store.evidence():
        if r['status'] in ('blocked','missing','metadata'):
            auto.append({'id':'source-'+r['id'][:10],'auto':True,'kind':'source_'+r['status'],'item':r['title'] or r['url'],'category':r['category'],
                         'need':'本機重新抓取或人工下載','url':r['url'],'note':r['note'],'impact':'證據未完整取得'})
    if config.get('identity_verified') is not True:
        auto.append({'id':'identity','auto':True,'kind':'identity','item':'官方公司身分 verify-identity','need':'交易所／MOPS 公司基本資料 HTTPS URL','impact':'facts／value／daily 會被擋'})
    manual=[g for g in manual if g.get('id') not in {a['id'] for a in auto}]
    out={'security':config['security'],'asof':asof,'generated':now(),'gaps':manual+auto,'partial':data['partial'],
         'rules':'年度財報 3/31、Q1 5/15、Q2 8/14、Q3 11/14（一般業）；年報依股東會日期，以 6/30 為檢查點'}
    dump(root/GAPS,out); write_todo(root,config,out)
    return {'statutory_missing':sum(g.get('kind')=='statutory_missing' for g in auto),'blocked_sources':sum(str(g.get('kind','')).startswith('source_') for g in auto),
            'partial':len(data['partial']),'manual':len(manual),'files':[GAPS,TODO]}

def write_todo(root,config,data):
    def rows(gs): return [f"| {g.get('item','')} | {g.get('mops_filename') or g.get('url') or ''} | {g.get('need','')} | {g.get('due') or ''} |" for g in gs]
    stat=[g for g in data['gaps'] if g.get('kind')=='statutory_missing']
    blocked=[g for g in data['gaps'] if str(g.get('kind','')).startswith('source_')]
    other=[g for g in data['gaps'] if g not in stat and g not in blocked]
    lines=[f"# {config['name']} {config['security']} 待下載清單",'',f"截止日 {data['asof']}；產生於 {data['generated']}。本機執行時先 dedupe-check，再 ingest。",'']
    if stat: lines+=['## 法定文件（MOPS）','','| 文件 | MOPS 檔名 | 取得方式 | 應公告日 |','|---|---|---|---|']+rows(stat)+['']
    if blocked: lines+=['## 先前被擋的來源','','| 來源 | 網址 | 處理 | |','|---|---|---|---|']+rows(blocked)+['']
    if data['partial']:
        lines+=['## 只讀到部分頁面','','| 文件 | 已讀頁 | 缺頁 | 說明 |','|---|---|---|---|']
        lines+=[f"| {p['doc']} | {p['pages_covered']}{'／'+str(p['total_pages']) if p.get('total_pages') else ''} | {p.get('missing') or ''} | {p.get('note') or ''} |" for p in data['partial']]+['']
    if other: lines+=['## 其他缺口','','| 項目 | | 需要 | |','|---|---|---|---|']+rows(other)+['']
    lines.append('非投資建議。')
    (Path(root)/TODO).write_text('\n'.join(lines)+'\n',encoding='utf-8')
