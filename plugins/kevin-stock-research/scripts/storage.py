"""Drive mirror of a research root. config.storage.drive_folder names the Drive folder; changes are found by SHA256.

Modes: local_sync copies changed files into a local Google Drive for desktop folder (binaries included);
connector lists small text files a host Drive connector can upload and writes 待手動上傳.md for the rest.
Nothing on Drive is ever deleted; files removed locally are only reported.
"""
from __future__ import annotations
import re, shutil
from pathlib import Path
from research import digest, dump, read, now

DEFAULT_FOLDER='投資組合-台股/{short}{ticker}/{short}{ticker}研究'
RECORD='Drive同步紀錄.json'
PENDING='待手動上傳.md'
EXCLUDE_DIRS={'runs','__pycache__','.git'}
EXCLUDE_NAMES={RECORD,PENDING,'.DS_Store'}
EXCLUDE_SUFFIX=('.tmp','.sqlite-journal','.db-journal','.lock')
TEXT_TYPES={'.md','.json','.html','.svg','.csv','.txt'}
CONNECTOR_MAX_BYTES=100_000

def short(config):
    from library import short_name
    return short_name(config)

def resolve_folder(config,template=None):
    t=template or (config.get('storage') or {}).get('drive_folder') or DEFAULT_FOLDER
    folder=t.format(short=short(config),name=config['name'],ticker=config['ticker'],market=config['market'])
    if folder.startswith(('/','\\')) or '..' in Path(folder).parts or re.match(r'^[A-Za-z]:',folder):
        raise ValueError('drive_folder must be a path inside My Drive, e.g. 投資組合-台股/竹陞6739/竹陞6739研究')
    return folder.replace('\\','/').strip('/')

def make_storage(config,drive_folder=None,local_sync_root=None,connector_max_bytes=None):
    old=dict(config.get('storage') or {})
    st={'drive_folder':resolve_folder(config,drive_folder or old.get('drive_folder')),
        'local_sync_root':local_sync_root if local_sync_root is not None else old.get('local_sync_root'),
        'connector_max_bytes':int(connector_max_bytes or old.get('connector_max_bytes') or CONNECTOR_MAX_BYTES)}
    if st['local_sync_root'] in ('','none'): st['local_sync_root']=None
    if st['connector_max_bytes']<1000: raise ValueError('connector_max_bytes too small')
    return st

def validate_storage(st):
    if not isinstance(st,dict) or not st.get('drive_folder'): raise ValueError('storage.drive_folder required')
    if '..' in Path(st['drive_folder']).parts or st['drive_folder'].startswith('/'): raise ValueError('invalid storage.drive_folder')
    return st

def files(root):
    root=Path(root); out=[]
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if not p.is_file() or any(x in EXCLUDE_DIRS for x in rel.parts[:-1]) or p.name in EXCLUDE_NAMES or p.name.endswith(EXCLUDE_SUFFIX) or p.name.startswith('~$'):
            continue
        out.append(rel.as_posix())
    return out

def load_record(root):
    p=Path(root)/RECORD
    return read(p) if p.exists() else {'drive_folder':None,'files':{}}

def plan(root,config):
    root=Path(root); st=make_storage(config); rec=load_record(root); held=rec.get('files',{})
    if rec.get('drive_folder') and rec['drive_folder']!=st['drive_folder']: held={}  # folder moved: everything is new there
    target=Path(st['local_sync_root'])/st['drive_folder'] if st['local_sync_root'] else None
    mode='local_sync' if st['local_sync_root'] and Path(st['local_sync_root']).is_dir() else 'connector'
    changed=[];unchanged=0;current=files(root)
    for rel in current:
        p=root/rel; sha=digest(p.read_bytes()); size=p.stat().st_size
        if held.get(rel,{}).get('sha256')==sha: unchanged+=1; continue
        item={'path':rel,'sha256':sha,'bytes':size,'drive_path':st['drive_folder']+'/'+rel,'status':'modified' if rel in held else 'new'}
        if held.get(rel,{}).get('drive_file_id'): item['replace_drive_file_id']=held[rel]['drive_file_id']
        if mode=='connector': item['via']='connector' if p.suffix.lower() in TEXT_TYPES and size<=st['connector_max_bytes'] else 'manual'
        else: item['via']='local_sync'
        changed.append(item)
    removed=sorted(set(held)-set(current))
    out={'mode':mode,'drive_folder':st['drive_folder'],'local_target':str(target) if target else None,'changed':changed,
         'unchanged':unchanged,'removed_locally':removed,'last_sync':rec.get('last_sync')}
    if st['local_sync_root'] and mode=='connector': out['warning']='local_sync_root 不存在（雲端環境或未安裝 Google Drive 桌面版），改用連接器／手動模式'
    return out

def sync(root,config,apply=False):
    root=Path(root); p=plan(root,config)
    if not apply:
        p['note']='dry-run：未複製、未改紀錄；確認後加 --apply'; return p
    rec=load_record(root)
    if rec.get('drive_folder')!=p['drive_folder']: rec={'drive_folder':p['drive_folder'],'files':{}}
    if p['mode']=='local_sync':
        target=Path(p['local_target'])
        for it in p['changed']:
            dest=target/it['path']; dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(root/it['path'],dest)
            if digest(dest.read_bytes())!=it['sha256']: raise ValueError('copy verification failed: '+it['path'])
            rec['files'][it['path']]={'sha256':it['sha256'],'bytes':it['bytes'],'synced_at':now(),'via':'local_sync'}
        rec['last_sync']=now(); dump(root/RECORD,rec); write_pending(root,p['drive_folder'],[])
        p['status']=f"copied {len(p['changed'])} files to {target}"
    else:
        pending=[it for it in p['changed']]
        write_pending(root,p['drive_folder'],pending)
        p['status']='connector mode: host uploads via=connector items, user uploads via=manual items, then drive-record each path'
    return p

def write_pending(root,folder,items):
    path=Path(root)/PENDING
    if not items:
        if path.exists(): path.unlink()
        return
    lines=['# 待上傳到 Google Drive','',f'目標資料夾：`{folder}`（產生於 {now()}）','',
           '`connector` 由對話中的 Drive 連接器上傳（文字檔、小於上限）；`manual` 需自行放入 Drive（二進位或過大）。上傳後執行 `drive-record --path …` 標記完成。',
           '連接器無法覆寫內容：已修改的檔案先上傳新檔，再把舊檔（舊 ID 欄）移到同資料夾的 `_舊版/`，不要刪除。','',
           '| 方式 | 檔案 | Drive 位置 | 大小 | 狀態 | 舊 ID |','|---|---|---|---|---|---|']
    for it in sorted(items,key=lambda x:(x['via'],x['path'])):
        lines.append(f"| {it['via']} | {it['path']} | {it['drive_path'].rsplit('/',1)[0]}/ | {it['bytes']:,} B | {'新增' if it['status']=='new' else '已修改'} | {it.get('replace_drive_file_id','')} |")
    lines+=['','非投資建議。']
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')

def record(root,config,paths,file_ids=None,via='connector'):
    """Mark files as present on Drive after a connector or manual upload (stores the bytes' SHA256 as uploaded)."""
    root=Path(root); st=make_storage(config); rec=load_record(root)
    if rec.get('drive_folder')!=st['drive_folder']: rec={'drive_folder':st['drive_folder'],'files':{}}
    ids=list(file_ids or [])
    if ids and len(ids)!=len(paths): raise ValueError('--file-id count must match --path count')
    done=[]
    for i,rel in enumerate(paths):
        rel=Path(rel).as_posix(); p=root/rel
        if not p.is_file() or rel not in files(root): raise ValueError('not a syncable file in root: '+rel)
        entry={'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size,'synced_at':now(),'via':via}
        if ids: entry['drive_file_id']=ids[i]
        rec['files'][rel]=entry; done.append(rel)
    rec['last_sync']=now(); dump(root/RECORD,rec)
    left=[it for it in plan(root,config)['changed']]
    write_pending(root,st['drive_folder'],left)
    return {'recorded':done,'still_pending':len(left)}
