"""Portable multi-security research workflow. No order execution or automatic scheduling."""
from __future__ import annotations
import argparse, copy, json, math, re, sqlite3, sys, uuid, zipfile
from datetime import date, datetime
from pathlib import Path
from research import VERSION, Store, read, dump, digest, identity, number, kevin_valuation, anchor_bases, DEFAULT_ANCHOR, LEGACY_ANCHOR, size_position, audit_model, update_copy

PLUGIN_ROOT=Path(__file__).resolve().parents[1]
MARKETS={'TWSE':('Asia/Taipei','TWD'),'TPEX':('Asia/Taipei','TWD'),
         'NYSE':('America/New_York','USD'),'NASDAQ':('America/New_York','USD')}
INDUSTRIES={'general','growth-manufacturing','semiconductor','semiconductor-equipment','datacenter-networking','osat','cyclical','financial','asset-based','loss-making'}
KEVIN_INDUSTRIES={'general','growth-manufacturing','semiconductor','semiconductor-equipment','datacenter-networking','osat'}
MODES={
 'quick':['identity','sources','thesis','report'],
 'full':['identity','sources','pdf-library','facts','thesis','engineering-visuals','valuation','integrated-deck','report'],
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
    if c.get('deck_style') is not None:
        st=json.loads((PLUGIN_ROOT/'profiles/deck_styles.json').read_text(encoding='utf-8'))
        ds=c['deck_style']
        if ds.get('palette') not in st['palettes'] or ds.get('font') not in st['fonts']: raise ValueError('deck_style needs palette 01–10 and font A/B/C')
    if c.get('storage') is not None:
        from storage import validate_storage
        validate_storage(c['storage'])
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
    from storage import make_storage
    c['storage']=make_storage(c)
    validate_config(c); root.mkdir(parents=True,exist_ok=True); dump(root/'config.json',c)
    s=Store(root);s.db.close()
    if not (root/'缺口清單.json').exists():dump(root/'缺口清單.json',{'security':sid,'asof':None,'gaps':[],'partial':[]})
    if not (root/'README.md').exists():
        import readme
        readme.write(root,c)
    return c

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

def resolve_hurdle(a,x,profile,cutoff):
    """v3.7b 超額門檻 = 類別 ETF 自身的 G_FY（剔除記憶體）。依序：inputs.hurdle_growth／anchor.hurdle_growth（單次覆寫）→
    同一份 anchor 的 etf_growth_fy → profiles/anchors.json 該類別的 latest_known.etf_growth_fy（最新已知值）。"""
    for where,src in (('inputs',x),('anchor',a)):
        if src.get('hurdle_growth') is not None:
            return {'growth':src['hurdle_growth'],'source':f'{where}.hurdle_growth (request override)','asof':src.get('hurdle_asof') or a.get('asof'),'override':True}
    if a.get('etf_growth_fy') is not None:
        return {'growth':a['etf_growth_fy'],'source':f"anchor.etf_growth_fy ({a.get('etf') or a.get('category')}, same anchor)",'asof':a.get('asof'),'override':False}
    c=(profile.get('categories') or {}).get(a.get('category')) or {}
    g=(c.get('latest_known') or {}).get('etf_growth_fy')
    if g is None:raise ValueError('etf_growth_fy required (v3.7b hurdle = category ETF G_FY ex-memory)')
    return {'growth':g,'source':f"profiles/anchors.json {a.get('category')} latest_known.etf_growth_fy",'asof':(profile.get('latest_known') or {}).get('asof'),'override':False}

def resolve_anchor(x,cutoff):
    """inputs.anchor（類別ETF＋當月 ETF 落後PE／內涵成長／大盤 P/E）轉成 base_pe、etf_growth_fy（v3.7b：類別 ETF 剔除記憶體後的 G_FY 即超額門檻）；
    anchor_method=legacy_dual_anchor 時才轉成舊 base_pe_p/base_pe_q。anchor 與直接輸入的 base 欄位擇一；hurdle_growth 可單次覆寫。"""
    if x.get('anchor') is None:return x,None
    if any(k in x for k in ('base_pe','etf_growth_fy','base_pe_p','base_pe_q')):raise ValueError('provide anchor or direct base_pe/hurdle_growth (legacy: base_pe_p/base_pe_q), not both')
    a=dict(x['anchor']);profile=read(PLUGIN_ROOT/'profiles/anchors.json')
    method=a.setdefault('anchor_method',x.get('anchor_method',DEFAULT_ANCHOR))
    if x.get('anchor_method',method)!=method:raise ValueError('anchor.anchor_method conflicts with inputs.anchor_method')
    if a.get('category') is not None:
        preset=profile['categories'].get(a['category'])
        if preset is None:raise ValueError('unknown anchor category: '+str(a['category']))
        a.setdefault('etf',preset['etf'])
        if method==LEGACY_ANCHOR:
            for k in ('ratio_p','ratio_q'):a.setdefault(k,profile['legacy_dual_anchor']['ratios'][a['category']][k])
    a.setdefault('rule',{k:profile['rule'][k] for k in ('high_ratio','low_ratio','high_adj','low_adj')})
    if not a.get('asof'):raise ValueError('anchor.asof (date of the ETF and market P/E) required')
    if method!=LEGACY_ANCHOR and not str(a.get('source') or '').strip():
        raise ValueError('anchor.source required for v3.7b (preferred: Kevin目標價_YYYY_MM.xlsx sheet 錨定ETF)')
    if iso(a['asof'])>iso(cutoff):raise ValueError('anchor date after valuation cutoff')
    fields=('category','etf','etf_pe','ratio_p','ratio_q','market_pe','market_median_pe','asof') if method==LEGACY_ANCHOR else            ('category','etf','etf_pe_trailing','etf_growth_ttm','market_pe','market_median_pe','holdings_asof','asof','source','excluded_themes')
    if method!=LEGACY_ANCHOR:
        h=resolve_hurdle(a,x,profile,cutoff)
        if h['asof'] and iso(h['asof'])>iso(cutoff):raise ValueError('hurdle date after valuation cutoff')
        a=dict(a,**({'hurdle_growth':h['growth']} if h['override'] else {'etf_growth_fy':h['growth']}))
    resolved={**anchor_bases(a),**{k:a.get(k) for k in fields},'age_days':(iso(cutoff)-iso(a['asof'])).days}
    if method!=LEGACY_ANCHOR:
        resolved.update(hurdle_source=h['source'],hurdle_asof=h['asof'],hurdle_age_days=(iso(cutoff)-iso(h['asof'])).days if h['asof'] else None)
    y={k:v for k,v in x.items() if k not in ('anchor','hurdle_growth','hurdle_asof')};y['anchor_method']=method
    if method==LEGACY_ANCHOR:y.update(base_pe_p=resolved['base_pe_p'],base_pe_q=resolved['base_pe_q'])
    else:
        y.update(base_pe=resolved['base_pe'])
        if resolved.get('hurdle_growth') is not None:y['hurdle_growth']=resolved['hurdle_growth']
        if resolved.get('etf_growth_fy') is not None:y['etf_growth_fy']=resolved['etf_growth_fy']
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
        if industry not in KEVIN_INDUSTRIES: return {**out,'reason':'industry not supported by Kevin model'}
        x,anchor=resolve_anchor(x,request['asof'])
        profile=read(PLUGIN_ROOT/'profiles/anchors.json')
        if x.get('anchor_method',DEFAULT_ANCHOR)!=LEGACY_ANCHOR and x.get('excess_cap') is None and profile.get('excess_cap') is not None:x=dict(x,excess_cap=profile['excess_cap'])
        try: numeric=kevin_valuation(x)
        except ValueError as exc:return {**out,'reason':str(exc)}
        if anchor:
            numeric['anchor']=anchor
            if anchor['age_days']>ANCHOR_STALE_DAYS:numeric['warnings'].append(f"anchor P/E is {anchor['age_days']} days old; refresh ETF and market P/E (Kevin目標價_YYYY_MM.xlsx 錨定ETF)")
            if (anchor.get('hurdle_age_days') or 0)>ANCHOR_STALE_DAYS:numeric['warnings'].append(f"excess-growth hurdle is {anchor['hurdle_age_days']} days old; supply the current month's etf_growth_fy")
            if anchor.get('hurdle_asof') and anchor.get('hurdle_asof')!=anchor.get('asof'):numeric['warnings'].append(f"hurdle date {anchor['hurdle_asof']} differs from anchor date {anchor['asof']}; use the same month's category ETF G_FY when available")
            if 'excluded_themes' in anchor and '記憶體' not in (anchor.get('excluded_themes') or []):numeric['warnings'].append('anchor does not state that memory-theme stocks were excluded (v3.7b rule)')
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

def visual_command(root,c,args):
    import visuals
    out=root/'工程圖解'
    if args.command=='visual-check':
        files=[Path(f) for f in args.file] if args.file else sorted(out.glob('*.svg'))
        return {str(f.name):visuals.check_svg(f.read_text(encoding='utf-8')) for f in files}
    fonts=visuals.load_fonts(args.font_dir)
    if args.command=='visual-build':
        results=[visuals.produce(read(f),out,c,fonts) for f in args.spec]
    else:
        files=[Path(f) for f in args.file] if args.file else sorted(out.glob('*.svg'))
        results=[visuals.outline_file(f,None,fonts,out/'PNG預覽'/(f.stem+'.png'),out/'原始碼') for f in files]
    record={'generated':datetime.now().isoformat(timespec='seconds'),'command':args.command,'font_source':fonts['source'],'results':results}
    dump(out/'驗證紀錄.json',record);return record

def deck_command(root,c,args):
    import deck
    if args.command=='deck-check':return deck.check_deck(args.file)
    if args.command=='deck-fonts':return deck.apply_fonts(args.file,deck.resolve_style({},c))
    result=deck.build_deck(read(args.spec),root/'整合簡報',c,root)
    result['render_qa']='not_requested'
    if args.pdf:
        pdf,status=deck.export_pdf(result['file']);result.update(pdf=pdf,render_qa=status)
    dump(root/'整合簡報'/'validation.json',result);return result

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
    a=sub.add_parser('ingest');a.add_argument('--manifest',required=True);a.add_argument('--known');a.add_argument('--force',action='store_true')
    a=sub.add_parser('dedupe-check');a.add_argument('--manifest',required=True);a.add_argument('--known')
    a=sub.add_parser('classify-pdfs');a.add_argument('--manifest');a.add_argument('--apply',action='store_true')
    a=sub.add_parser('set-industry');a.add_argument('--industry',choices=sorted(INDUSTRIES),required=True)
    a=sub.add_parser('set-storage');a.add_argument('--drive-folder');a.add_argument('--local-sync-root');a.add_argument('--connector-max-bytes',type=int)
    a=sub.add_parser('drive-sync');a.add_argument('--apply',action='store_true')
    a=sub.add_parser('drive-record');a.add_argument('--path',nargs='+',required=True);a.add_argument('--file-id',nargs='*');a.add_argument('--via',choices=['connector','manual'],default='connector')
    a=sub.add_parser('gaps');a.add_argument('--asof',required=True);a.add_argument('--years',type=int,default=2)
    a=sub.add_parser('coverage-set');a.add_argument('--doc',required=True);a.add_argument('--pages',required=True);a.add_argument('--total',type=int);a.add_argument('--missing');a.add_argument('--note',default='')
    sub.add_parser('readme')
    a=sub.add_parser('set-deck-style');a.add_argument('--palette',required=True);a.add_argument('--font',required=True);a.add_argument('--cjk-font')
    a=sub.add_parser('visual-build');a.add_argument('--spec',required=True,nargs='+');a.add_argument('--font-dir')
    a=sub.add_parser('visual-outline');a.add_argument('--file',nargs='*');a.add_argument('--font-dir')
    a=sub.add_parser('visual-check');a.add_argument('--file',nargs='*')
    a=sub.add_parser('deck-build');a.add_argument('--spec',required=True);a.add_argument('--pdf',action='store_true')
    a=sub.add_parser('deck-check');a.add_argument('--file',required=True)
    a=sub.add_parser('deck-fonts');a.add_argument('--file',required=True)
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
                from library import Known, original_name
                ids=[];skipped=[];known=Known(s,c,read(args.known) if args.known else None)
                for raw in read(args.manifest):
                    item=raw.copy()
                    if item.get('security')!=c['security']:raise ValueError('manifest security mismatch')
                    local=item.pop('local_path',None);orig=item.pop('original_filename',None)
                    if local: ids.append(s.ingest(Path(local).read_bytes(),**item))
                    elif item.get('status') in ('metadata','missing','blocked'):ids.append(s.ingest(None,**item))
                    else:
                        reason=None if args.force else known.has(orig or original_name(item))
                        if reason:skipped.append({'url':item['url'],'reason':reason});continue
                        ids.append(s.fetch(**item))
                s.export();result={'evidence_ids':ids,'skipped_already_held':skipped}
            elif args.command=='dedupe-check':
                from library import dedupe_check
                result=dedupe_check(s,c,read(args.manifest),read(args.known) if args.known else None)
            elif args.command=='set-industry':
                c['industry']=args.industry;validate_config(c);dump(root/'config.json',c)
                result={'status':'saved','industry':args.industry,'profile':read(PLUGIN_ROOT/'profiles/industries'/f'{args.industry}.json')}
            elif args.command=='set-storage':
                from storage import make_storage
                c['storage']=make_storage(c,args.drive_folder,args.local_sync_root,args.connector_max_bytes)
                validate_config(c);dump(root/'config.json',c);result={'status':'saved','storage':c['storage']}
            elif args.command=='drive-sync':
                from storage import sync
                result=sync(root,c,args.apply)
            elif args.command=='drive-record':
                from storage import record
                result=record(root,c,args.path,args.file_id,args.via)
            elif args.command=='gaps':
                from gaps import refresh
                iso(args.asof);result=refresh(s,c,args.asof,args.years)
            elif args.command=='coverage-set':
                from gaps import coverage_set
                result=coverage_set(root,c,args.doc,args.pages,args.total,args.missing,args.note)
            elif args.command=='readme':
                import readme
                result=readme.write(root,c)
            elif args.command=='set-deck-style':
                c['deck_style']={'palette':args.palette,'font':args.font,**({'cjk_font':args.cjk_font} if args.cjk_font else {})}
                validate_config(c);dump(root/'config.json',c);result={'status':'saved','deck_style':c['deck_style']}
            elif args.command in ('visual-build','visual-outline','visual-check'):
                result=visual_command(root,c,args)
            elif args.command in ('deck-build','deck-check','deck-fonts'):
                result=deck_command(root,c,args)
            elif args.command=='classify-pdfs':
                from library import classify
                result=classify(s,c,read(args.manifest) if args.manifest else None,args.apply)
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
