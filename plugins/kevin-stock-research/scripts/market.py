"""Market boundary: validated calendars and normalized imports; TWSE live adapter."""
from datetime import date
from research import daily, number
from workflow import evidence_row, finite

def validate_calendar(calendar,market,asof):
    if calendar.get('market')!=market or calendar.get('verified') is not True or not calendar.get('source_id'):
        raise ValueError('verified market calendar with source_id required')
    day=date.fromisoformat(asof)
    start=date.fromisoformat(calendar['coverage_start']);end=date.fromisoformat(calendar['coverage_end'])
    if not start<=day<=end:raise ValueError('calendar does not cover requested date')
    days=calendar['open_dates']
    if days!=sorted(set(days)):raise ValueError('open_dates must be unique and ordered')
    if any(not start<=date.fromisoformat(x)<=end for x in days):raise ValueError('calendar session outside coverage')
    if calendar.get('complete') is not True:raise ValueError('partial calendar cannot prove closure')
    return asof in days

def collect_daily(store,config,asof,calendar):
    is_open=validate_calendar(calendar,config['market'],asof)
    evidence_row(store,calendar['source_id'],config['security'])
    if not is_open:return {'status':'closed','security':config['security'],'data_date':asof,'daily_updated':False,'calendar_source_id':calendar['source_id']}
    if config['market']!='TWSE':
        return {'status':'unsupported','market':config['market'],'reason':'Live adapter not validated. Import verified market snapshot; never call TWSE for other markets.'}
    return daily(store,{**config,'_calendar_verified_open':True},asof)

def import_market(store,config,payload,asof):
    if payload.get('security')!=config['security']:raise ValueError('market snapshot security mismatch')
    if payload.get('currency')!=config['quote_currency']:raise ValueError('market currency mismatch')
    if not date.fromisoformat(payload['data_date'])<=date.fromisoformat(payload['available_at'])<=date.fromisoformat(asof):raise ValueError('market snapshot after cutoff or invalid availability')
    if payload.get('verified') is not True:raise ValueError('market snapshot unverified')
    evidence_row(store,payload['source_id'],config['security'])
    if payload.get('volume_unit')!='shares':raise ValueError('normalize volume to shares')
    finite(payload['close'],'close',0);finite(payload['volume'],'volume',0)
    if payload['close']<=0:raise ValueError('close must be positive')
    sid=store.snapshot(config['security'],'verified_market_import',payload['data_date'],payload)
    return {'status':'imported','snapshot_id':sid,'data_date':payload['data_date'],'stale_for_asof':payload['data_date']!=asof}
