"""Portable multi-security research workflow. No order execution or automatic scheduling."""
from __future__ import annotations
import argparse, copy, json, math, re, sqlite3, sys, uuid, zipfile
from datetime import date, datetime
from pathlib import Path
from research import VERSION, Store, read, dump, digest, identity, number, kevin_valuation, anchor_bases, size_position, audit_model, update_copy

PLUGIN_ROOT=Path(__file__).resolve().parents[1]
MARKETS={'TWSE':('Asia/Taipei','TWD'),'TPEX':('Asia/Taipei','TWD'),
         'NYSE':('America/New_York','USD'),'NASDAQ':('America/New_York','USD')}
INDUSTRIES={'general','growth-manufacturing','semiconductor','cyclical','financial','asset-based','loss-making'}
MODES={
 'quick':['identity','sources','thesis','report'],
 'full':['identity','sources','facts','thesis','valuation','report'],
 'refresh':['identity','changed-sources','facts','thesis-diff','valuation','report'],
 'monitor':['identity','calendar','market','events','notification'],
 'compare':['identity','facts','comparability','report'],
 'position':['identity','valuation','thesis','portfolio','report']}

def iso(value):
    return date.fromisoformat(value)

def finite(value,name,minimum=None):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError(name+' must be a finite JSON number')
    if minimum is not None and value<minimum: raise ValueError(name+' below minimum')
    return value

def capability(market):
    return {'research':'agent_with_verified_evidence','facts':'validated_import',
            'valuation':'kevin_dual_anchor_or_scenario_pe_pb_nav',
            'live_market':'twse_candidate_requires_per_run_validation' if market=='TWSE' else 'unsupported_use_verified_import',
            'portfolio':'same_currency_combined_proposals','scheduling':'host_specific_user_request_required'}

def validate_config(c):
    if c.get('schema_version')!=2: raise ValueError('schema_version 2 required; use migrate first')
    if c.get('security')!=identity(c['market'],c['ticker']): raise ValueError('security mismatch')
    if c.get('instrument_type')!='common_stock': raise ValueError('only common_stock supported; ADR/ETF/REIT require a separately validated profile')
    if c.get('industry') not in INDUSTRIES: raise ValueError('unknown industry profile')
    if not str(c.get('name','')).strip(): raise ValueError('company name required')
    for k in ('quote_currency','reporting_currency'):
        if not re.fullmatch('[A-Z]{3}',c.get(k,'')): raise ValueError('ISO currency required')
    iso('2000-'+c['fiscal_year_end'])
    if c.get('exchange_timezone')!=MARKETS[c['market']][0]: raise ValueError('market timezone mismatch')
    if c.get('identity_verified') and (not c.get('identity_source') or not c.get('identity_verified_at')):
        raise ValueError('verified identity needs official source and verification date')
    if c.get('identity_verified_at'): iso(c['identity_verified_at'])
    return c

def onboard(root,market,ticker,name,industry='general',reporting_currency=None,fiscal_year_end='12-31'):
    root=Path(root); sid=identity(market,ticker)
    if (root/'config.json').exists() or (root/'research.sqlite').exists(): raise ValueError('root already contains research; do not reinitialize')
    tz,currency=MARKETS[market]
    c={'schema_version':2,'version':VERSION,'security':sid,'market':market,'ticker':ticker,'name':name,
       'instrument_type':'common_stock','industry':industry,'identity_verified':False,'identity_source':None,'identity_verified_at':None,
       'exchange_timezone':tz,'report_timezone':'Asia/Taipei','quote_currency':currency,
       'reporting_currency':reporting_currency or currency,'fiscal_year_end':fiscal_year_end,
       'model_profile':None,'schedule_enabled':False,'valuation_alert_change':0.1,'capabilities':capability(market)}
    validate_config(c); root.mkdir(parents=True,exist_ok=True); dump(root/'config.json',c)
    s=Store(root);s.db.close();return c

def config_at(root,verified=False):
    c=validate_config(read(Path(root)/'config.json'))
    if verified and c.get('identity_verified') is not True: raise ValueError('verify security identity from an official source first')
    return c

def evidence_row(store,source_id,security):
    row=store.db.execute('SELECT * FROM evidence WHERE id=?',(source_id,)).fetchone()
    if not row or row['identity']!=security: raise ValueError('source_id missing or belongs to another security')
    if row['status']!='full' or not row['path']: raise ValueError('verified fact requires full acquired evidence')
    path=(store.root/row['path']).resolve()
    if not path.is_relative_to(store.root.resolve()) or not path.is_file(): raise ValueError('invalid evidence path')
    if digest(path.read_bytes())!=row['sha256']: raise ValueError('evidence hash mismatch')
    return dict(row)

def validate_fact(f,c,asof,store=None):
    required=('security','metric','value','currency','unit','scope','period_start','period_end',
              'available_at','basis','source_id','locator','verified','revision_basis')
    if any(k not in f for k in required): raise ValueError('missing fact fields')
    registry=read(PLUGIN_ROOT/'profiles/metrics.json')
    metric=registry.get(f['metric'])
    if metric is None: raise ValueError('unregistered metric')
    if f['security']!=c['security']: raise ValueError('fact security mismatch')
    finite(f['value'],'value')
    if f['verified'] is not True or not f['locator'] or not f['revision_basis']: raise ValueError('unverified fact or missing provenance')
    if f['currency']!=c['reporting_currency']: raise ValueError('currency mismatch; convert explicitly with FX evidence')
    if f['unit']!=metric['unit']: raise ValueError('normalize to registered unit before import')
    if f['scope'] not in ('consolidated','parent','parent_attributable'): raise ValueError('invalid scope')
    if f['basis'] not in metric['bases']: raise ValueError('basis not valid for metric')
    if iso(f['period_start'])>iso(f['period_end']) or iso(f['period_end'])>iso(f['available_at']) or iso(f['available_at'])>iso(asof):
        raise ValueError('invalid period or look-ahead evidence')
    if metric['type']=='stock' and f['period_start']!=f['period_end']: raise ValueError('stock fact requires point-in-time period')
    if store: evidence_row(store,f['source_id'],c['security'])
    return {**f,'metric_type':metric['type'],'fiscal_year_end':c['fiscal_year_end']}

def validate_mapping(w,sha,profile):
    if not profile or profile.get('verified') is not True: raise ValueError('verified mapping profile required')
    for k in ('profile_id','version','security','workbook_sha256','sheet','header_row','identity_column','identity_value','expected_headers','inputs','expected_formulas'):
        if k not in profile: raise ValueError('mapping missing '+k)
    market,ticker=profile['security'].split(':');identity(market,ticker)
    if not profile['profile_id'] or not isinstance(profile['version'],int) or profile['version']<1 or not profile['expected_headers']:
        raise ValueError('mapping identity, version and header checks required')
    if not re.fullmatch('[A-Z]{1,3}',profile['identity_column']) or not isinstance(profile['header_row'],int) or profile['header_row']<1:
        raise ValueError('invalid identity column or header row')
    if str(profile['identity_value']) not in (ticker,profile['security']): raise ValueError('mapping identity value mismatches security')
    if sha!=profile['workbook_sha256']: raise ValueError('workbook changed; remap and review new version')
    sheet=w[profile['sheet']]
    for cell,value in profile['expected_headers'].items():
        if sheet[cell].value!=value: raise ValueError('template header mismatch: '+cell)
    matches=[i for i in range(profile['header_row']+1,sheet.max_row+1)
             if str(sheet[f"{profile['identity_column']}{i}"].value).strip()==str(profile['identity_value'])]
    if len(matches)!=1: raise ValueError('stock row missing or ambiguous')
    row=matches[0]; inputs={}
    for metric,item in profile['inputs'].items():
        col=item['column']
        if not re.fullmatch('[A-Z]{1,3}',col) or not item.get('unit'): raise ValueError('invalid input mapping')
        key=sheet.title+'!'+col+str(row)
        if key in inputs: raise ValueError('duplicate mapped input')
        inputs[key]={**item,'metric':metric}
    if not inputs: raise ValueError('mapping has no inputs')
    for cell,formula in profile['expected_formulas'].items():
        sn,ref=cell.split('!')
        if w[sn][ref].value!=formula: raise ValueError('formula fingerprint mismatch')
    return inputs

def mapped_update(root,original,destination,mapping_path,changes_path):
    c=config_at(root,True); profile=read(mapping_path); changes=read(changes_path)
    if profile.get('security')!=c['security']: raise ValueError('mapping belongs to another stock')
    import openpyxl
    with zipfile.ZipFile(original) as z:
        if any('externalLink' in n or 'vbaProject' in n for n in z.namelist()): raise ValueError('external links/macros need separate review')
    workbook=openpyxl.load_workbook(original)
    try: allowed=validate_mapping(workbook,digest(Path(original).read_bytes()),profile)
    finally: workbook.close()
    s=Store(root)
    try:
        for item in changes: evidence_row(s,item['source_id'],c['security'])
    finally:s.db.close()
    update_copy(original,destination,changes,list(allowed),profile)
    return {'status':'updated_copy_requires_recalculation','destination':str(destination),'mapping_version':profile['version']}

ANCHOR_STALE_DAYS=45

def resolve_anchor(x,cutoff):
    """inputs.anchor（類別預設比例＋當月 ETF／大盤 P/E）轉成 base_pe_p/base_pe_q；與直接輸入兩個 base 擇一。"""
    if x.get('anchor') is None:return x,None
    if 'base_pe_p' in x or 'base_pe_q' in x:raise ValueError('provide anchor or base_pe_p/base_pe_q, not both')
    a=dict(x['anchor']);profile=read(PLUGIN_ROOT/'profiles/anchors.json')
    if a.get('category') is not None:
        preset=profile['categories'].get(a['category'])
        if preset is None:raise ValueError('unknown anchor category: '+str(a['category']))
        for k in ('etf','ratio_p','ratio_q'):a.setdefault(k,preset[k])
    a.setdefault('rule',{k:profile['rule'][k] for k in ('high_ratio','low_ratio','high_adj','low_adj')})
    if not a.get('asof'):raise ValueError('anchor.asof (date of the ETF and market P/E) required')
    if iso(a['asof'])>iso(cutoff):raise ValueError('anchor date after valuation cutoff')
    resolved={**anchor_bases(a),**{k:a.get(k) for k in ('category','etf','etf_pe','ratio_p','ratio_q','market_pe','market_median_pe','asof')},
              'age_days':(iso(cutoff)-iso(a['asof'])).days}
    y={k:v for k,v in x.items() if k!='anchor'};y.update(base_pe_p=resolved['base_pe_p'],base_pe_q=resolved['base_pe_q'])
    return y,resolved

def value_company(request):
    method=request['method']; x=request['inputs']; out={'method':method,'status':'not_applicable','numeric_output':None}
    if request.get('assumptions_verified') is not True: return {**out,'reason':'unverified assumptions'}
    if not request.get('source_ids') or not request.get('assumptions_asof') or not request.get('currency'):
        raise ValueError('valuation provenance, date and currency required')
    iso(request['assumptions_asof'])
    if iso(request['assumptions_asof'])>iso(request['asof']):raise ValueError('assumption date after cutoff')
    industry=request.get('industry','general')
    if industry not in INDUSTRIES:raise ValueError('unknown valuation industry')
    candidates=read(PLUGIN_ROOT/'profiles/industries'/f'{industry}.json')['candidate_methods']
    if method not in candidates:return {**out,'reason':'method not enabled for this industry profile'}
    if method=='kevin_legacy':
        if industry not in ('growth-manufacturing','semiconductor','general'): return {**out,'reason':'industry not supported by Kevin model'}
        x,anchor=resolve_anchor(x,request['asof'])
        try: numeric=kevin_valuation(x)
        except ValueError as exc:return {**out,'reason':str(exc)}
        if anchor:
            numeric['anchor']=anchor
            if anchor['age_days']>ANCHOR_STALE_DAYS:numeric['warnings'].append(f"anchor P/E is {anchor['age_days']} days old; refresh ETF and market P/E")
    elif method in ('scenario_pe','scenario_pb'):
        metric='eps' if method=='scenario_pe' else 'book_value_per_share'
        for k in (metric,'multiple_low','multiple_high'):finite(x[k],k,0)
        if x[metric]<=0:return {**out,'reason':'positive '+metric+' required'}
        if x['multiple_low']<=0 or x['multiple_low']>x['multiple_high']: raise ValueError('invalid multiples')
        numeric={'price_low':x[metric]*x['multiple_low'],'price_high':x[metric]*x['multiple_high']}
    elif method=='nav':
        for k in ('asset_value','liabilities','shares','discount'):finite(x[k],k,0)
        if x['shares']<=0 or x['discount']>=1 or x['asset_value']<=x['liabilities']:return {**out,'reason':'NAV inputs not applicable'}
        numeric={'nav_per_share':(x['asset_value']-x['liabilities'])/x['shares']*(1-x['discount'])}
    else:return {**out,'reason':'method not implemented; no automatic numeric fallback'}
    return {**out,'status':'calculated_scenario_not_trade_signal','numeric_output':numeric,
            'currency':request['currency'],'assumptions_asof':request['assumptions_asof'],'source_ids':request['source_ids']}

def plan_batch(payload):
    """One atomic *proposal*, sequential caller-prioritized budget, no portfolio mutation."""
    account=payload['account']; requests=payload['requests']; iso(account['asof'])
    for k in ('investable_assets','available_cash','loss_budget_remaining'):finite(account[k],k,0)
    if account['investable_assets']<=0 or not account.get('account_id') or not account.get('snapshot_id'):raise ValueError('invalid account snapshot')
    if not re.fullmatch('[A-Z]{3}',account.get('currency','')):raise ValueError('ISO account currency required')
    cash=account['available_cash']; loss=account['loss_budget_remaining']; sectors=copy.deepcopy(account['sector_values'])
    for key,value in sectors.items():finite(value,'sector '+key,0)
    seen=set();plans=[]
    for r in requests:
        sid=r['security'];identity(*sid.split(':'))
        if sid in seen:raise ValueError('duplicate security in batch')
        seen.add(sid)
        if r['currency']!=account['currency']:raise ValueError('cross-currency proposals require explicit FX conversion')
        if r['sector'] not in sectors:raise ValueError('unknown sector exposure')
        p={**r['personal'],'investable_assets':account['investable_assets'],'available_cash':cash,
           'sector_value':sectors[r['sector']],'loss_budget_remaining':loss}
        for key,value in p.items():
            if isinstance(value,(int,float)):finite(value,key)
        result=size_position(p,r['signal']);n=result.get('shares') or 0
        if n:
            price=r['signal']['price'];cost=result['amount']
            reserved_loss=n*(p['risk_per_share']+price*(p['fee_rate']+p['sell_fee_rate']+p['sell_tax_rate']))+2*p['minimum_fee']
            cash-=cost;loss-=reserved_loss;sectors[r['sector']]+=n*price
            if cash < -1e-7 or loss < -1e-7: raise AssertionError('combined budgets exceeded')
        plans.append({'security':sid,**result,'currency':account['currency']})
    return {'status':'combined_proposal_only','account_id':account['account_id'],'snapshot_id':account['snapshot_id'],
            'snapshot_hash':digest(json.dumps(account,sort_keys=True).encode()),'currency':account['currency'],
            'plans':plans,'remaining_cash':cash,'remaining_loss_budget':loss,'sector_values_after':sectors,
            'holdings_updated':False,'cash_reserved':False,
            'constraint':'This entire proposal is mutually exclusive with other batches using this snapshot; refresh account before execution.'}

def compare_facts(datasets,metric):
    candidates=[f for group in datasets for f in group if f['metric']==metric]
    if not candidates:return {'status':'missing','rows':[]}
    if any(f.get('verified') is not True or not f.get('source_id') or not f.get('available_at') for f in candidates):
        return {'status':'unverified','rows':candidates}
    keys=('metric','currency','unit','scope','basis','period_start','period_end','revision_basis')
    signatures={tuple(f.get(k) for k in keys) for f in candidates}
    if len(signatures)!=1:return {'status':'not_comparable','reason':'period, revision, basis, unit, scope or currency mismatch','rows':candidates}
    if len({f['security'] for f in candidates})!=len(candidates): return {'status':'ambiguous_revisions','rows':candidates}
    return {'status':'comparable','rows':sorted(candidates,key=lambda f:f['security'])}

def plan(root,mode,asof):
    c=config_at(root);iso(asof)
    run_id=uuid.uuid4().hex
    result={'run_id':run_id,'security':c['security'],'mode':mode,'asof':asof,'status':'planned_not_executed',
            'resolved_config':c,'steps':MODES[mode],
            'industry_profile':read(PLUGIN_ROOT/'profiles/industries'/f"{c['industry']}.json"),
            'blockers':[] if c.get('identity_verified') else ['official security identity not yet verified']}
    dump(Path(root)/'runs'/run_id/'plan.json',result)
    return result

def migrate(root,apply=False):
    path=Path(root)/'config.json';old=read(path)
    if old.get('schema_version')==2:return {'status':'already_current'}
    market=old['market'];tz,currency=MARKETS[market]
    new={**old,'schema_version':2,'version':VERSION,'instrument_type':'common_stock','industry':'general',
         'identity_verified':False,'identity_source':None,'identity_verified_at':None,
         'exchange_timezone':tz,'report_timezone':'Asia/Taipei','quote_currency':currency,
         'reporting_currency':currency,'fiscal_year_end':'12-31','model_profile':None,'schedule_enabled':False,
         'capabilities':capability(market),'migration_note':'Reverify identity, fiscal year, model mapping and host automations. Existing host schedules are not changed by this migration.'}
    validate_config(new)
    if apply:
        backup=path.with_name('config.v1.'+digest(path.read_bytes())[:12]+'.json')
        if not backup.exists():backup.write_bytes(path.read_bytes())
        dump(path,new)
    return {'status':'migrated' if apply else 'dry_run','config':new}

def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True)
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('init');a.add_argument('--market',choices=list(MARKETS),required=True);a.add_argument('--ticker',required=True);a.add_argument('--name',required=True);a.add_argument('--industry',choices=sorted(INDUSTRIES),default='general');a.add_argument('--reporting-currency');a.add_argument('--fiscal-year-end',default='12-31')
    a=sub.add_parser('verify-identity');a.add_argument('--source',required=True);a.add_argument('--date',required=True)
    a=sub.add_parser('plan');a.add_argument('--mode',choices=list(MODES),default='full');a.add_argument('--asof',required=True)
    a=sub.add_parser('ingest');a.add_argument('--manifest',required=True)
    a=sub.add_parser('facts');a.add_argument('--file',required=True);a.add_argument('--asof',required=True)
    a=sub.add_parser('daily');a.add_argument('--date',required=True);a.add_argument('--calendar',required=True)
    a=sub.add_parser('import-market');a.add_argument('--file',required=True);a.add_argument('--asof',required=True)
    a=sub.add_parser('audit-model');a.add_argument('file')
    a=sub.add_parser('update-model');a.add_argument('--original',required=True);a.add_argument('--destination',required=True);a.add_argument('--mapping',required=True);a.add_argument('--changes',required=True)
    a=sub.add_parser('value');a.add_argument('--request',required=True)
    a=sub.add_parser('batch-size');a.add_argument('--file',required=True)
    a=sub.add_parser('compare');a.add_argument('--files',nargs='+',required=True);a.add_argument('--metric',required=True)
    a=sub.add_parser('monitor');a.add_argument('--file',required=True);a.add_argument('--date',required=True);a.add_argument('--slot',choices=['20:30','22:00','manual'],default='manual')
    a=sub.add_parser('fill');a.add_argument('--record',required=True)
    a=sub.add_parser('extract');a.add_argument('--evidence-id',required=True)
    a=sub.add_parser('ack');a.add_argument('alert_id')
    sub.add_parser('pending');sub.add_parser('export');sub.add_parser('capabilities')
    a=sub.add_parser('migrate');a.add_argument('--apply',action='store_true')
    args=p.parse_args();root=Path(args.root)
    if root.resolve().is_relative_to(PLUGIN_ROOT):raise ValueError('research data must be outside the plugin directory')
    if args.command=='init':result=onboard(root,args.market,args.ticker,args.name,args.industry,args.reporting_currency,args.fiscal_year_end)
    elif args.command=='migrate':result=migrate(root,args.apply)
    elif args.command=='plan':result=plan(root,args.mode,args.asof)
    elif args.command=='batch-size':result=plan_batch(read(args.file))
    elif args.command=='compare':result=compare_facts([read(f) for f in args.files],args.metric)
    elif args.command=='update-model':result=mapped_update(root,args.original,args.destination,args.mapping,args.changes)
    else:
        c=config_at(root);s=Store(root)
        try:
            if args.command=='verify-identity':
                iso(args.date)
                if not args.source.startswith('https://'):raise ValueError('official HTTPS identity source required')
                c.update(identity_verified=True,identity_source=args.source,identity_verified_at=args.date);dump(root/'config.json',c)
                result={'status':'user_or_agent_attestation_saved','security':c['security'],'note':'This command records prior verification; it does not itself verify the website.'}
            elif args.command=='capabilities':result=capability(c['market'])
            elif args.command=='ingest':
                ids=[]
                for raw in read(args.manifest):
                    item=raw.copy()
                    if item.get('security')!=c['security']:raise ValueError('manifest security mismatch')
                    local=item.pop('local_path',None)
                    if local: ids.append(s.ingest(Path(local).read_bytes(),**item))
                    elif item.get('status') in ('metadata','missing','blocked'):ids.append(s.ingest(None,**item))
                    else:ids.append(s.fetch(**item))
                s.export();result={'evidence_ids':ids}
            elif args.command=='facts':
                config_at(root,True);facts=[validate_fact(f,c,args.asof,s) for f in read(args.file)]
                sha=digest(json.dumps(facts,sort_keys=True).encode());dump(root/'財務數據'/('facts-'+sha[:16]+'.json'),facts)
                result={'status':'validated','facts':len(facts),'hash':sha}
            elif args.command=='daily':
                config_at(root,True)
                from market import collect_daily
                result=collect_daily(s,c,args.date,read(args.calendar))
            elif args.command=='import-market':
                config_at(root,True)
                from market import import_market
                result=import_market(s,c,read(args.file),args.asof)
            elif args.command=='audit-model':result=audit_model(args.file,root/'模型/model-audit.json',c['ticker'])
            elif args.command=='value':
                config_at(root,True);req=read(args.request)
                if req.get('security')!=c['security'] or req.get('industry')!=c['industry']:raise ValueError('valuation profile mismatch')
                if req.get('currency')!=c['quote_currency']:raise ValueError('valuation currency mismatch')
                for eid in req.get('source_ids',[]):evidence_row(s,eid,c['security'])
                result=value_company(req)
                dump(root/'模型'/('valuation-'+uuid.uuid4().hex+'.json'),result)
            elif args.command=='monitor':
                config_at(root,True)
                from monitor import transition
                result=transition(s,c['security'],read(args.file),root/'monitor-state.json',args.date,args.slot,c.get('valuation_alert_change',.1))
            elif args.command=='fill':s.fill(read(args.record));result={'status':'confirmed_fill_recorded'}
            elif args.command=='extract':result=s.extract_pdf(args.evidence_id)
            elif args.command=='pending':result=s.pending(c['security'])
            elif args.command=='ack':s.acknowledge(args.alert_id);result={'status':'acknowledged'}
            elif args.command=='export':result=s.export()
        finally:s.db.close()
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
