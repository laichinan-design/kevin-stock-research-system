import copy, json, tempfile, unittest, subprocess, sys
from pathlib import Path
from unittest.mock import patch
import openpyxl
from research import Store, dump, digest, rolling, single_quarter, update_copy, ledger
from workflow import onboard, validate_config, validate_fact, validate_mapping, value_company, plan_batch, compare_facts, migrate, plan, config_at
from monitor import transition
from market import validate_calendar, collect_daily, import_market

class MultiSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.c=onboard(self.root/'one','TWSE','2330','Fixture company','semiconductor')
        self.s=Store(self.root/'one')
    def tearDown(self):self.s.db.close();self.tmp.cleanup()
    def source(self):return self.s.ingest(b'official fixture evidence',security='TWSE:2330',category='fixture',url='https://example.test/verified',suffix='.txt')
    def fact(self):return dict(security='TWSE:2330',metric='revenue',value=100,currency='TWD',unit='currency_units',scope='consolidated',period_start='2026-01-01',period_end='2026-03-31',available_at='2026-05-01',basis='quarter',source_id=self.source(),locator='page 1',verified=True,revision_basis='original-2026')
    def test_market_profiles_independent(self):
        for i,(market,ticker) in enumerate([('TPEX','1234'),('NASDAQ','TEST'),('NYSE','TEST.A')]):
            c=onboard(self.root/str(i),market,ticker,'Fixture');self.assertEqual(c['security'],market+':'+ticker)
        self.assertFalse(self.c['identity_verified'])
    def test_no_reinit(self):
        with self.assertRaises(ValueError):onboard(self.root/'one','TWSE','3653','Other')
    def test_cross_security_ingest_rejected(self):
        with self.assertRaises(ValueError):self.s.ingest(b'data',security='TWSE:3653',category='x',url='https://example.test')
    def test_cross_security_fill_rejected(self):
        with self.assertRaises(ValueError):self.s.fill({'security':'TWSE:3653'})
    def test_empty_full_rejected(self):
        with self.assertRaises(ValueError):self.s.ingest(None,security='TWSE:2330',category='x',url='https://example.test')
    def test_invalid_pdf_rejected(self):
        with self.assertRaises(Exception):self.s.ingest(b'%PDF-not-a-pdf',security='TWSE:2330',category='x',url='https://example.test',suffix='.pdf')
    def test_metadata_can_be_empty(self):
        eid=self.s.ingest(None,security='TWSE:2330',category='x',url='https://example.test',status='metadata');self.assertTrue(eid)
    def test_fact_verified_and_source_present(self):
        f=self.fact();self.assertEqual(validate_fact(f,self.c,'2026-09-30',self.s)['metric_type'],'flow')
    def test_future_fact_rejected(self):
        f=self.fact();f['available_at']='2026-10-02'
        with self.assertRaises(ValueError):validate_fact(f,self.c,'2026-09-30',self.s)
    def test_wrong_fact_currency_rejected(self):
        f=self.fact();f['currency']='USD'
        with self.assertRaises(ValueError):validate_fact(f,self.c,'2026-09-30',self.s)
    def test_fake_source_rejected(self):
        f=self.fact();f['source_id']='missing'
        with self.assertRaises(ValueError):validate_fact(f,self.c,'2026-09-30',self.s)
    def test_tampered_source_rejected(self):
        f=self.fact();r=self.s.evidence()[0];(self.s.root/r['path']).write_bytes(b'tampered')
        with self.assertRaises(ValueError):validate_fact(f,self.c,'2026-09-30',self.s)
    def test_no_balance_sheet_subtraction(self):
        a=dict(metric='liabilities',basis='ytd',quarter=2,value=300)
        with self.assertRaises(ValueError):single_quarter(a,{**a,'quarter':1,'value':110})
    def test_revision_mismatch_rejected(self):
        a=dict(security='TWSE:2330',metric='revenue',basis='ytd',quarter=2,value=300,revision_basis='restated')
        with self.assertRaises(ValueError):single_quarter(a,{**a,'quarter':1,'value':110,'revision_basis':'original'})
    def test_rolling_missing_session(self):
        self.assertIsNone(rolling([{'data_date':'2026-09-28','flow':10},{'data_date':'2026-09-30','flow':20}],'flow',2,['2026-09-29','2026-09-30']))
    def test_rolling_requires_calendar(self):
        self.assertIsNone(rolling([{'data_date':'2026-09-30','flow':20}],'flow',1))
    def test_rolling_complete(self):
        self.assertEqual(rolling([{'data_date':'2026-09-29','flow':10},{'data_date':'2026-09-30','flow':20}],'flow',2,['2026-09-29','2026-09-30']),30)
    def test_rolling_revision_ambiguous(self):
        with self.assertRaises(ValueError):rolling([{'data_date':'2026-09-30','flow':10},{'data_date':'2026-09-30','flow':20}],'flow',1,['2026-09-30'])
    def test_monitor_cross_security_state(self):
        state=self.root/'state.json';transition(self.s,'TWSE:2330',{'decision':'observe'},state,'2026-09-30','manual')
        other=Store(self.root/'other')
        try:
            with self.assertRaises(ValueError):transition(other,'TWSE:3653',{'decision':'observe'},state,'2026-09-30','manual')
        finally:other.db.close()
    def test_monitor_recovery_new_failure(self):
        state=self.root/'state.json'
        for day,failures in [('2026-09-28',['x']),('2026-09-29',[]),('2026-09-30',['x'])]:transition(self.s,'TWSE:2330',{'source_failures':failures},state,day,'manual')
        self.assertEqual(len(self.s.pending('TWSE:2330')),2)
    def test_monitor_stale_run_rejected(self):
        state=self.root/'state.json';transition(self.s,'TWSE:2330',{},state,'2026-09-30','manual')
        with self.assertRaises(ValueError):transition(self.s,'TWSE:2330',{},state,'2026-09-29','manual')
    def test_calendar_partial_rejected(self):
        with self.assertRaises(ValueError):validate_calendar(dict(market='TWSE',verified=True,source_id='x',coverage_start='2026-09-01',coverage_end='2026-09-30',open_dates=[],complete=False),'TWSE','2026-09-30')
    def test_market_import_and_cutoff(self):
        p=dict(security='TWSE:2330',currency='TWD',data_date='2026-09-30',available_at='2026-09-30',verified=True,source_id=self.source(),volume_unit='shares',close=100,volume=200)
        self.assertEqual(import_market(self.s,self.c,p,'2026-09-30')['status'],'imported')
        with self.assertRaises(ValueError):import_market(self.s,self.c,p,'2026-09-29')
    def test_tpex_does_not_call_twse(self):
        c=onboard(self.root/'tpex','TPEX','1234','Fixture');s=Store(self.root/'tpex')
        try:
            eid=s.ingest(b'calendar',security=c['security'],category='calendar',url='https://example.test',suffix='.txt')
            cal=dict(market='TPEX',verified=True,complete=True,source_id=eid,coverage_start='2026-09-30',coverage_end='2026-09-30',open_dates=['2026-09-30'])
            with patch('market.daily',side_effect=AssertionError('wrong network')):self.assertEqual(collect_daily(s,c,'2026-09-30',cal)['status'],'unsupported')
        finally:s.db.close()
    def test_comparison_unit_mismatch(self):
        a=self.fact();b={**a,'security':'TWSE:3653','unit':'thousand'};self.assertEqual(compare_facts([[a],[b]],'revenue')['status'],'not_comparable')
    def test_comparison_same_basis(self):
        a=self.fact();b={**a,'security':'TWSE:3653'};self.assertEqual(compare_facts([[a],[b]],'revenue')['status'],'comparable')
    def test_plan_is_not_execution(self):self.assertEqual(plan(self.s.root,'full','2026-09-30')['status'],'planned_not_executed')
    def test_ledger_rejects_mixed_security(self):
        with self.assertRaises(ValueError):ledger([{'security':'TWSE:2330'},{'security':'TWSE:3653'}],100)
    def test_migrate_dry_run_preserves_file(self):
        root=self.root/'old';root.mkdir();dump(root/'config.json',dict(market='TWSE',ticker='2330',name='Fixture',security='TWSE:2330'))
        before=(root/'config.json').read_bytes();migrate(root);self.assertEqual((root/'config.json').read_bytes(),before)
        migrate(root,True);self.assertEqual(config_at(root)['schema_version'],2);self.assertFalse(config_at(root)['identity_verified'])
    def test_cli_init_and_plan(self):
        script=Path(__file__).with_name('workflow.py');root=self.root/'cli'
        args=[sys.executable,'-B',str(script),'--root',str(root)]
        a=subprocess.run(args+['init','--market','NASDAQ','--ticker','TEST','--name','Fixture'],capture_output=True)
        self.assertEqual(a.returncode,0,a.stderr)
        b=subprocess.run(args+['plan','--asof','2026-09-30'],capture_output=True)
        self.assertEqual(b.returncode,0,b.stderr);self.assertEqual(json.loads(b.stdout)['status'],'planned_not_executed')
    def test_cli_evidence_to_valuation_end_to_end(self):
        script=Path(__file__).with_name('workflow.py');root=self.root/'pipeline'
        def run(*args):
            r=subprocess.run([sys.executable,'-B',str(script),'--root',str(root),*args],capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
        run('init','--market','TWSE','--ticker','2330','--name','Fixture','--industry','semiconductor')
        run('verify-identity','--source','https://example.test/official-fixture','--date','2026-09-30')
        text=self.root/'evidence.txt';text.write_text('Fixture revenue 100, EPS 10; not real financial data.',encoding='utf-8')
        manifest=self.root/'sources.json';dump(manifest,[dict(security='TWSE:2330',category='fixture',url='https://example.test/official-fixture',local_path=str(text),suffix='.txt',published='2026-05-01')])
        eid=run('ingest','--manifest',str(manifest))['evidence_ids'][0]
        f=self.fact();f['source_id']=eid;facts=self.root/'facts.json';dump(facts,[f])
        self.assertEqual(run('facts','--file',str(facts),'--asof','2026-09-30')['facts'],1)
        value=self.root/'value.json';dump(value,dict(security='TWSE:2330',industry='semiconductor',method='scenario_pe',inputs=dict(eps=10,multiple_low=12,multiple_high=20),currency='TWD',assumptions_verified=True,assumptions_asof='2026-09-30',asof='2026-09-30',source_ids=[eid]))
        self.assertEqual(run('value','--request',str(value))['numeric_output']['price_low'],120)
        state=self.root/'state.json';dump(state,dict(security='TWSE:2330',decision='observe'))
        run('monitor','--file',str(state),'--date','2026-09-30');run('monitor','--file',str(state),'--date','2026-09-30')
        pending=run('pending');self.assertEqual(len(pending),1);run('ack',pending[0]['id']);self.assertEqual(run('pending'),[])

class MappingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.src=self.root/'a.xlsx'
        self.w=openpyxl.Workbook();s=self.w.active;s['A1']='ticker';s['B1']='price';s['A2']='2330';s['B2']=100;s['C2']='=B2*2';self.w.save(self.src)
        self.p=dict(profile_id='fixture',version=1,verified=True,security='TWSE:2330',workbook_sha256=digest(self.src.read_bytes()),sheet='Sheet',header_row=1,identity_column='A',identity_value='2330',expected_headers={'A1':'ticker','B1':'price'},inputs={'price':{'column':'B','unit':'TWD'}},expected_formulas={'Sheet!C2':'=B2*2'})
        self.change=dict(sheet='Sheet',cell='B2',value=110,security='TWSE:2330',source_id='fixture',asof='2026-09-30',basis='TWD')
    def tearDown(self):self.w.close();self.tmp.cleanup()
    def test_mapping_unique_stock(self):self.assertIn('Sheet!B2',validate_mapping(self.w,self.p['workbook_sha256'],self.p))
    def test_missing_profile_blocks_legacy_bypass(self):
        with self.assertRaises(ValueError):update_copy(self.src,self.root/'b.xlsx',[self.change],['Sheet!B2'])
    def test_other_stock_profile_rejected(self):
        with self.assertRaises(ValueError):validate_mapping(self.w,self.p['workbook_sha256'],{**self.p,'security':'TWSE:3653'})
    def test_duplicate_stock_rejected(self):
        self.w.active['A3']='2330'
        with self.assertRaises(ValueError):validate_mapping(self.w,self.p['workbook_sha256'],self.p)
    def test_workbook_changed_rejected(self):
        with self.assertRaises(ValueError):validate_mapping(self.w,'different-hash',self.p)
    def test_header_changed_rejected(self):
        self.w.active['B1']='cost'
        with self.assertRaises(ValueError):validate_mapping(self.w,self.p['workbook_sha256'],self.p)
    def test_wrong_change_security_rejected(self):
        with self.assertRaises(ValueError):update_copy(self.src,self.root/'b.xlsx',[{**self.change,'security':'TWSE:3653'}],['Sheet!B2'],self.p)
    def test_wrong_unit_rejected(self):
        with self.assertRaises(ValueError):update_copy(self.src,self.root/'b.xlsx',[{**self.change,'basis':'USD'}],['Sheet!B2'],self.p)
    def test_formula_not_changed(self):
        update_copy(self.src,self.root/'b.xlsx',[self.change],['Sheet!B2'],self.p)
        self.assertEqual(digest(self.src.read_bytes()),self.p['workbook_sha256']);self.assertEqual(openpyxl.load_workbook(self.root/'b.xlsx').active['C2'].value,'=B2*2')

class ValuationPortfolioTests(unittest.TestCase):
    def valuation(self):return dict(method='scenario_pe',inputs=dict(eps=10,multiple_low=12,multiple_high=20),industry='semiconductor',assumptions_verified=True,assumptions_asof='2026-09-30',asof='2026-09-30',currency='TWD',source_ids=['fixture'])
    def test_pe(self):self.assertEqual(value_company(self.valuation())['numeric_output']['price_low'],120)
    def kevin(self,industry='general'):
        inputs=dict(revenue_ytd=6811534,months=8,consolidated_margin=1475886/5037705,margin_basis='consolidated',owner_ratio=1,capital_thousands=646000,par=10,previous_eps=18,
                    anchor=dict(category='portfolio',etf_pe=22,market_pe=31.26,market_median_pe=17,asof='2026-09-11'))
        return dict(method='kevin_legacy',industry=industry,inputs=inputs,currency='TWD',assumptions_verified=True,assumptions_asof='2026-09-29',asof='2026-09-29',source_ids=['fixture'])
    def test_kevin_anchor_preset_and_general_industry(self):
        r=value_company(self.kevin());n=r['numeric_output']
        self.assertEqual(r['status'],'calculated_scenario_not_trade_signal');self.assertEqual(n['anchor']['etf'],'0050')
        self.assertAlmostEqual(n['anchor']['base_pe_p'],14.025);self.assertAlmostEqual(n['anchor']['base_pe_q'],10.285);self.assertAlmostEqual(n['model_value'],1529.39,places=1)
    def test_kevin_premium_through_workflow(self):
        r=self.kevin();r['inputs']['target_premium']=1.5
        self.assertAlmostEqual(value_company(r)['numeric_output']['scenarios']['A']['model_value_with_premium'],2294.08,places=1)
    def test_kevin_eps_multiplier_returns_reason(self):
        r=self.kevin();r['inputs']['multiplier']=1.5;out=value_company(r)
        self.assertEqual(out['status'],'not_applicable');self.assertIn('target_premium',out['reason'])
    def test_kevin_anchor_dates(self):
        future=self.kevin();future['inputs']['anchor']['asof']='2026-09-30'
        with self.assertRaises(ValueError):value_company(future)
        stale=self.kevin();stale['inputs']['anchor']['asof']='2026-07-01'
        self.assertTrue(any('days old' in w for w in value_company(stale)['numeric_output']['warnings']))
    def test_kevin_anchor_conflicts(self):
        both=self.kevin();both['inputs']['base_pe_p']=14
        with self.assertRaises(ValueError):value_company(both)
        unknown=self.kevin();unknown['inputs']['anchor']['category']='unknown'
        with self.assertRaises(ValueError):value_company(unknown)
    def test_kevin_enabled_for_equipment_and_networking(self):
        base=value_company(self.kevin())['numeric_output']['model_value']
        for industry in ('semiconductor-equipment','datacenter-networking','osat'):
            r=value_company(self.kevin(industry))
            self.assertEqual(r['status'],'calculated_scenario_not_trade_signal',industry);self.assertAlmostEqual(r['numeric_output']['model_value'],base)
    def test_industry_profiles_match_registry(self):
        from workflow import INDUSTRIES,KEVIN_INDUSTRIES,PLUGIN_ROOT
        files={p.stem for p in (PLUGIN_ROOT/'profiles/industries').glob('*.json')};self.assertEqual(files,INDUSTRIES)
        for name in INDUSTRIES:
            d=json.loads((PLUGIN_ROOT/'profiles/industries'/f'{name}.json').read_text(encoding='utf-8'))
            self.assertEqual(d['id'],name);self.assertEqual('kevin_legacy' in d['candidate_methods'],name in KEVIN_INDUSTRIES,name)
    def test_kevin_still_blocked_for_cyclical(self):
        self.assertEqual(value_company(self.kevin('cyclical'))['status'],'not_applicable')
    def test_negative_eps_no_target(self):
        r=self.valuation();r['inputs']['eps']=0;self.assertEqual(value_company(r)['status'],'not_applicable')
    def test_financial_rejects_pe_route(self):self.assertEqual(value_company({**self.valuation(),'industry':'financial'})['status'],'not_applicable')
    def test_future_assumption_rejected(self):
        r=self.valuation();r['asof']='2026-09-29'
        with self.assertRaises(ValueError):value_company(r)
    def test_pb(self):
        r=self.valuation();r.update(method='scenario_pb',industry='financial',inputs=dict(book_value_per_share=20,multiple_low=1,multiple_high=2));self.assertEqual(value_company(r)['numeric_output']['price_high'],40)
    def test_nav(self):
        r=self.valuation();r.update(method='nav',industry='asset-based',inputs=dict(asset_value=1000,liabilities=200,shares=10,discount=.2));self.assertEqual(value_company(r)['numeric_output']['nav_per_share'],64)
    def batch(self):
        personal=dict(holding_shares=0,average_cost=0,single_stock_limit=1,sector_limit=1,risk_per_share=1,core_ratio=.8,tactical_ratio=.2,batch_budget=10000,fee_rate=0,minimum_fee=0,sell_fee_rate=0,sell_tax_rate=0)
        signal=dict(model_verified=True,data_current=True,thesis_valid=True,price=100,buy_max=110)
        return dict(account=dict(account_id='fixture',snapshot_id='s1',asof='2026-09-30',currency='TWD',investable_assets=100000,available_cash=10000,loss_budget_remaining=100000,sector_values={'tech':0}),requests=[dict(security='TWSE:2330',currency='TWD',sector='tech',personal=personal,signal=signal),dict(security='TWSE:3653',currency='TWD',sector='tech',personal=personal.copy(),signal=signal.copy())])
    def test_shared_cash_not_double_spent(self):
        p=self.batch();before=copy.deepcopy(p);r=plan_batch(p);self.assertEqual(sum(x['amount'] for x in r['plans']),10000);self.assertEqual(r['plans'][1]['shares'],0);self.assertEqual(before,p);self.assertFalse(r['cash_reserved'])
    def test_shared_sector_room(self):
        p=self.batch();p['account']['sector_values']['tech']=94000;p['requests'][0]['personal']['batch_budget']=4000
        r=plan_batch(p);self.assertLessEqual(r['sector_values_after']['tech'],100000)
    def test_shared_loss_budget(self):
        p=self.batch();p['account']['loss_budget_remaining']=75;p['requests'][0]['personal']['batch_budget']=4000
        r=plan_batch(p);self.assertLessEqual(sum(x['shares'] for x in r['plans']),75)
    def test_fx_requires_explicit_handling(self):
        p=self.batch();p['requests'][1]['currency']='USD'
        with self.assertRaises(ValueError):plan_batch(p)
    def test_duplicate_batch_rejected(self):
        p=self.batch();p['requests'][1]['security']='TWSE:2330'
        with self.assertRaises(ValueError):plan_batch(p)

if __name__=='__main__':unittest.main(verbosity=2)
