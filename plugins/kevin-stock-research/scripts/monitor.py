"""Transactional notification outbox and security-bound monitor state."""
import json
from datetime import date
from pathlib import Path
from research import read,dump,digest,number,now

def compare(previous,current,threshold=.10):
    events=[]
    for key in ('decision','risk_state','zone'):
        if current.get(key) is not None and previous.get(key)!=current[key]:events.append({'kind':key,'value':current[key]})
    a,b=number(previous.get('valuation')),number(current.get('valuation'))
    if a is not None and a>0 and b is not None and abs(b/a-1)>=threshold:events.append({'kind':'valuation','from':a,'to':b,'change':b/a-1})
    old=set(previous.get('source_failures',[]));new=set(current.get('source_failures',[]))
    for source in sorted(new-old):events.append({'kind':'source_failure','source':source})
    for event in current.get('announcements',[]):
        if event not in previous.get('announcements',[]):events.append({'kind':'announcement','id':event})
    return events

def transition(store,security,current,state_path,run_date,slot,threshold=.10):
    store.check_security(security);date.fromisoformat(run_date);state_path=Path(state_path)
    if slot not in ('20:30','22:00','manual') or not 0<threshold<=1:raise ValueError('invalid monitor parameters')
    if current.get('security',security)!=security:raise ValueError('current snapshot belongs to another security')
    if state_path.exists():
        saved=read(state_path)
        if saved.get('security')!=security:raise ValueError('state identity mismatch or v1 state needs migration')
    key=str(state_path.resolve())
    store.db.execute('CREATE TABLE IF NOT EXISTS monitor_states(path TEXT PRIMARY KEY, security TEXT NOT NULL, payload TEXT NOT NULL)')
    store.db.commit();store.db.execute('BEGIN IMMEDIATE')
    try:
        row=store.db.execute('SELECT security,payload FROM monitor_states WHERE path=?',(key,)).fetchone()
        if row and row['security']!=security:raise ValueError('state database identity mismatch')
        state=json.loads(row['payload']) if row else (read(state_path) if state_path.exists() else {'schema_version':2,'security':security,'sequence':0,'latest':{},'retry_dates':[],'weekly_dates':[]})
        if state.get('last_run_date','')>run_date:raise ValueError('out-of-order monitor run; historical runs must use a separate root')
        if slot=='22:00':
            if run_date in state['retry_dates'] or not state.get('retry_needed',False) or state.get('last_run_date')!=run_date:
                store.db.rollback();return {'skipped':True,'reason':'no outstanding retry or already attempted'}
            state['retry_dates'].append(run_date)
        events=compare(state['latest'],current,threshold)
        def queue(kind,event_key,payload):
            aid=digest((security+'|'+kind+'|'+event_key).encode())
            store.db.execute('INSERT OR IGNORE INTO alerts VALUES(?,?,?,?,?,NULL)',(aid,security,kind,json.dumps(payload,ensure_ascii=False),now()))
        for event in events:
            state['sequence']+=1;queue(event['kind'],str(state['sequence'])+':'+digest(json.dumps(event,sort_keys=True).encode()),event)
        weekly=date.fromisoformat(run_date).weekday()==4 and run_date not in state['weekly_dates']
        if weekly:
            queue('weekly',run_date,{'date':run_date,'status':'weekly report ready to prepare'});state['weekly_dates'].append(run_date)
        state.update(latest=current,last_run_date=run_date,retry_needed=bool(current.get('source_failures')) and slot!='22:00')
        store.db.execute('INSERT OR REPLACE INTO monitor_states VALUES(?,?,?)',(key,security,json.dumps(state,ensure_ascii=False)))
        store.db.commit()
    except Exception:
        store.db.rollback();raise
    # SQLite is authoritative; this file is an inspectable mirror only.
    dump(state_path,state)
    return {'events':events,'weekly_required':weekly,'retry_needed':state['retry_needed'],'pending':store.pending(security)}
