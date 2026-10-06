import unittest,tempfile,json,math
from pathlib import Path
from unittest.mock import patch
from research import *

class EvidenceTests(unittest.TestCase):
 def setUp(self): self.temp=tempfile.TemporaryDirectory(); self.s=Store(self.temp.name)
 def tearDown(self): self.s.db.close(); self.temp.cleanup()
 def test_dedup_and_revision(self):
  kw=dict(security='TWSE:3653',category='test',url='https://example.test/a',suffix='.txt')
  a=self.s.ingest(b'v1',**kw); self.assertEqual(a,self.s.ingest(b'v1',**kw)); b=self.s.ingest(b'v2',**kw); self.assertNotEqual(a,b); self.assertEqual(len(self.s.evidence()),2); self.assertEqual(len(list((self.s.root/'原始文件').glob('*'))),2)
 def test_same_content_two_sources(self):
  for u in ('a','b'): self.s.ingest(b'v1',security='TWSE:3653',category='t',url='https://example.test/'+u,suffix='.txt')
  self.assertEqual(len(self.s.evidence()),2); self.assertEqual(len(list((self.s.root/'原始文件').glob('*'))),1)
 def test_html_not_pdf(self):
  with self.assertRaises(ValueError): self.s.ingest(b'<html>login</html>',security='TWSE:3653',category='t',url='https://test',suffix='.pdf')
 def test_no_fake_download_on_failure(self):
  with patch('urllib.request.urlopen',side_effect=TimeoutError('offline')): self.s.fetch('https://test',security='TWSE:3653',category='t')
  r=self.s.evidence()[0]; self.assertEqual(r['status'],'blocked'); self.assertEqual(r['path'],'')
 def test_revision_snapshots(self):
  a=self.s.snapshot('TWSE:3653','margin','2026-09-30',{'balance':2}); self.assertEqual(a,self.s.snapshot('TWSE:3653','margin','2026-09-30',{'balance':2})); self.s.snapshot('TWSE:3653','margin','2026-09-30',{'balance':3}); self.assertEqual(self.s.db.execute('select count(*) from snapshots').fetchone()[0],2)
 def test_notification_ack(self):
  a=self.s.alert('TWSE:3653','risk','event-1',{'x':1}); self.s.alert('TWSE:3653','risk','event-1',{'x':1}); self.assertEqual(len(self.s.pending()),1); self.s.acknowledge(a); self.s.alert('TWSE:3653','risk','event-1',{'x':1}); self.assertEqual(self.s.pending(),[])
 def test_fill_requires_confirmation_and_is_idempotent(self):
  f={'id':'a','security':'TWSE:3653','date':'2026-09-30','side':'buy','shares':10,'price':100,'fees':1,'tax':0,'source':'user trade','confirmed':False}
  with self.assertRaises(ValueError):self.s.fill(f)
  f['confirmed']=True; self.s.fill(f);self.s.fill(f);self.assertEqual(self.s.db.execute('select count(*) from fills').fetchone()[0],1)
  f['price']=101
  with self.assertRaises(ValueError):self.s.fill(f)
 def test_closed_no_network(self):
  with patch('urllib.request.urlopen',side_effect=AssertionError('network must not run')): r=daily(self.s,{'market':'TWSE','ticker':'3653'},'2026-09-27')
  self.assertFalse(r['daily_updated'])

class CalculationTests(unittest.TestCase):
 def test_periods(self): self.assertEqual(period(115,quarter=2,basis='ytd'),{'year':2026,'quarter':2,'month':None,'basis':'ytd'})
 def test_cumulative_conversion(self):
  a={'security':'TWSE:3653','metric':'revenue','basis':'ytd','year':2026,'quarter':2,'value':300,'currency':'NT$','unit':'thousand','scope':'consolidated'};b={**a,'quarter':1,'value':110};self.assertEqual(single_quarter(a,b),190)
  with self.assertRaises(ValueError): single_quarter({**a,'metric':'eps'},{**b,'metric':'eps'})
  with self.assertRaises(ValueError): single_quarter(a,{**b,'year':2025})
 def test_net_income_basis(self):
  x={'revenue_ytd':800,'months':8,'consolidated_margin':.25,'owner_ratio':.9,'capital_thousands':100,'par':10,'previous_eps':20,'base_pe':20,'hurdle_growth':.3,'price':500,'margin_basis':'consolidated'}
  self.assertAlmostEqual(kevin_calculate(x)['eps'],27)
  with self.assertRaises(ValueError):kevin_calculate({**x,'margin_basis':'parent'})
  self.assertEqual(kevin_calculate({**x,'previous_eps':40})['branch'],'below_anchor_growth')
  z=kevin_calculate({**x,'previous_eps':0});self.assertEqual(z['growth'],1.0);self.assertTrue(any('100%' in w for w in z['warnings']))
  with self.assertRaisesRegex(ValueError,'EPS <= 0'):kevin_calculate({**x,'consolidated_margin':-.1})
 def test_missing_values_not_zero(self): self.assertIsNone(number('--')); self.assertIsNone(number('nan')); self.assertIsNone(rolling([{'data_date':'2026-09-30','flow':None}],'flow',1))
 def test_grouped_margin_fields(self):
  j={'stat':'OK','date':'20260930','tables':[{'fields':['代號','今日餘額','今日餘額'],'groups':[{'title':'股票','span':1},{'title':'融資','span':1},{'title':'融券','span':1}],'data':[['3653','100','4']]}]}
  r=parse_twse(j,'3653','2026-09-30'); self.assertEqual(r['融資_今日餘額'],'100'); self.assertEqual(r['融券_今日餘額'],'4')
 def test_stale_response(self):
  with self.assertRaises(ValueError):parse_twse({'stat':'OK','date':'20260929','fields':['id'],'data':[['3653']]},'3653','2026-09-30')
  with self.assertRaises(ValueError):parse_twse({'stat':'很抱歉，沒有符合條件的資料!'},'3653','2026-09-30')
 def test_return_accounting(self):
  f=[{'id':'a','date':'2026-09-01','side':'buy','shares':10,'price':100,'fees':1,'tax':0},{'id':'b','date':'2026-09-02','side':'sell','shares':4,'price':120,'fees':1,'tax':1}]
  r=ledger(f,90); self.assertAlmostEqual(r['realized_pnl'],77.6); self.assertAlmostEqual(r['unrealized_pnl'],-60.6);self.assertAlmostEqual(r['total_pnl'],17)
 def test_size_missing(self): self.assertIsNone(size_position({},{}).get('shares'))
 def test_risk_caps(self):
  p={'investable_assets':100000,'available_cash':5000,'holding_shares':10,'average_cost':100,'single_stock_limit':.05,'sector_limit':.1,'sector_value':8000,'loss_budget_remaining':200,'risk_per_share':20,'core_ratio':.8,'tactical_ratio':.2,'batch_budget':4000,'fee_rate':.001,'minimum_fee':1,'sell_fee_rate':.001,'sell_tax_rate':.003}
  sig={'model_verified':True,'data_current':True,'thesis_valid':True,'price':100,'buy_max':110};r=size_position(p,sig);self.assertEqual(r['shares'],9);self.assertLessEqual(r['amount'],p['available_cash']);self.assertLessEqual(r['stock_exposure_after'],.05);self.assertLessEqual(r['sector_exposure_after'],.1);self.assertFalse(r['holdings_updated'])
  self.assertEqual(size_position(p,{**sig,'price':120})['shares'],0)
  self.assertIsNone(size_position(p,{**sig,'model_verified':False})['shares'])

class TransitionTests(unittest.TestCase):
 def test_retry_once_and_no_repeated_notifications(self):
  from monitor import transition
  with tempfile.TemporaryDirectory() as p:
   s=Store(p);sp=Path(p)/'state.json';cur={'source_failures':['margin'],'decision':'conditional'}
   a=transition(s,'TWSE:3653',cur,sp,'2026-09-30','20:30');n=len(s.pending());self.assertTrue(a['retry_needed'])
   transition(s,'TWSE:3653',cur,sp,'2026-09-30','20:30');self.assertEqual(len(s.pending()),n)
   b=transition(s,'TWSE:3653',cur,sp,'2026-09-30','22:00');self.assertFalse(b['retry_needed']);self.assertTrue(transition(s,'TWSE:3653',cur,sp,'2026-09-30','22:00')['skipped']);s.db.close()
 def test_weekly_exactly_once(self):
  from monitor import transition
  with tempfile.TemporaryDirectory() as p:
   s=Store(p);sp=Path(p)/'state.json';transition(s,'TWSE:3653',{},sp,'2026-10-02','20:30');transition(s,'TWSE:3653',{},sp,'2026-10-02','20:30');self.assertEqual(len(s.pending()),1);s.db.close()
 def test_model_update_preserves_original(self):
  import openpyxl
  with tempfile.TemporaryDirectory() as p:
   a=Path(p)/'a.xlsx';b=Path(p)/'b.xlsx';w=openpyxl.Workbook();w.active['A1']='ticker';w.active['B1']='price';w.active['A2']='3653';w.active['B2']=100;w.active['C2']='=B2*2';w.save(a);h=digest(a.read_bytes())
   profile={'profile_id':'test','version':1,'verified':True,'security':'TWSE:3653','workbook_sha256':h,'sheet':'Sheet','header_row':1,'identity_column':'A','identity_value':'3653','expected_headers':{'A1':'ticker','B1':'price'},'inputs':{'price':{'column':'B','unit':'TWD'}},'expected_formulas':{'Sheet!C2':'=B2*2'}}
   update_copy(a,b,[{'sheet':'Sheet','cell':'B2','value':110,'source_id':'test','asof':'2026-09-30','basis':'TWD','security':'TWSE:3653'}],['Sheet!B2'],profile);self.assertEqual(h,digest(a.read_bytes()));self.assertEqual(openpyxl.load_workbook(b).active['C2'].value,'=B2*2')
   with self.assertRaises(ValueError):update_copy(a,Path(p)/'bad.xlsx',[{'sheet':'Sheet','cell':'C2','value':1,'source_id':'test','asof':'2026-09-30','basis':'x','security':'TWSE:3653'}],['Sheet!C2'],profile)
 def test_valuation_change_and_source_recovery(self):
  from monitor import compare
  self.assertEqual(compare({'valuation':100},{'valuation':109}),[])
  self.assertEqual(compare({'valuation':100},{'valuation':111})[0]['kind'],'valuation')
  self.assertEqual(compare({'source_failures':['x']},{'source_failures':['x']}),[])
  self.assertEqual(compare({'valuation':100},{'valuation':106},threshold=.05)[0]['kind'],'valuation')

# Kevin v3.7b 回歸案例：數字取自公開財報（2026H1／1-8月營收）與帳戶 skill kevin-stock-pricing-model v3.7b 範例（2026-10-03 錨定值）；非研究結論、非投資建議。
PORTFOLIO=dict(base_pe=20.999471,hurdle_growth=.485004)
POTENTIAL=dict(base_pe=29.091102,hurdle_growth=.602024)
CPO=dict(base_pe=26.852505,hurdle_growth=.528864)
BELLWETHER=dict(revenue_ytd=6811534,months=8,consolidated_margin=1475886/5037705,margin_basis='consolidated',owner_ratio=1,capital_thousands=646000,par=10,previous_eps=18,price=1165,**PORTFOLIO)
SONGCHUAN_H1=dict(scope='consolidated',revenue=4117008,pretax=585489,tax=147119,net_income=438370,nonrecurring=dict(fx=52237,disposals=12601,fvtpl=-146))
SONGCHUAN_Q2=dict(scope='consolidated',revenue=2259879,pretax=356148,tax=94262,net_income=261886,nonrecurring=dict(disposals=7453,fx=7030,fvtpl=-137))
SONGCHUAN=dict(revenue_ytd=5975262,months=8,owner_ratio=440369/438370,nci_loss_verified=True,capital_thousands=797460,par=10,price=290.5,earnings_quality=SONGCHUAN_H1,**POTENTIAL)
SUMMARY_0050=dict(trailing_pe=29.22953,growth_ttm=.18313,growth_prior=.485004,coverage=.8968,excluded_themes=['記憶體'],market_pe=31.26,market_median_pe=17)

class KevinModelTests(unittest.TestCase):
 def test_anchor_summary(self):
  b=anchor_base(SUMMARY_0050)
  self.assertEqual(b['m_adj'],.85);self.assertAlmostEqual(b['forward_pe'],24.7053,places=3);self.assertAlmostEqual(b['base_pe'],20.9995,places=3);self.assertEqual(b['warnings'],[])
  self.assertTrue(any('記憶體' in w for w in anchor_base({**SUMMARY_0050,'excluded_themes':[]})['warnings']))
  self.assertAlmostEqual(anchor_base({k:v for k,v in SUMMARY_0050.items() if k not in ('market_pe','market_median_pe')}|{'market_pe_ratio':1.839})['base_pe'],20.9995,places=3)
 def test_anchor_retired_dual_fields(self):
  with self.assertRaisesRegex(ValueError,'retired'):anchor_base({**SUMMARY_0050,'ratio_p':.75})
  with self.assertRaisesRegex(ValueError,'retired'):anchor_base({**SUMMARY_0050,'etf_pe':22})
  with self.assertRaisesRegex(ValueError,'retired'):kevin_calculate({**BELLWETHER,'base_pe_p':14.025})
  with self.assertRaisesRegex(ValueError,'retired'):kevin_calculate({**BELLWETHER,'base_pe_low':14.025})
 def test_anchor_m_adj_boundaries(self):
  m=lambda mp:anchor_base({**SUMMARY_0050,'market_pe':mp,'market_median_pe':10})['m_adj']
  self.assertEqual(m(13),1.0); self.assertEqual(m(13.1),.85); self.assertEqual(m(8),1.0); self.assertEqual(m(7.9),1.15)
  with self.assertRaises(ValueError): anchor_base({**SUMMARY_0050,'trailing_pe':0})
 def test_anchor_constituents_exclude_memory(self):
  rows=[dict(code='2330',weight=.5,price=100,eps_ttm=4,eps_forecast=5,eps_prior=3),dict(code='2317',weight=.3,price=50,eps_ttm=2.5,eps_forecast=2.5,eps_prior=2.5),
        dict(code='2408',weight=.2,price=50,eps_ttm=1,eps_forecast=10,eps_prior=.5)]
  b=anchor_base(dict(constituents=rows,market_pe_ratio=1),{'2408'})
  self.assertEqual(b['excluded'],['2408']);self.assertEqual(b['excluded_themes'],['記憶體']);self.assertAlmostEqual(b['coverage'],.8)
  ttm=(.5*.04+.3*.05)/.8;fwd=(.5*.05+.3*.05)/.8;prior=(.5*.03+.3*.05)/.8
  self.assertAlmostEqual(b['trailing_pe'],1/ttm);self.assertAlmostEqual(b['growth_ttm'],fwd/ttm-1);self.assertAlmostEqual(b['growth_prior'],fwd/prior-1)
  kept=anchor_base(dict(constituents=rows,market_pe_ratio=1,exclude_memory=False),{'2408'});self.assertEqual(kept['excluded'],[]);self.assertTrue(kept['warnings'])
  with self.assertRaises(ValueError):anchor_base(dict(constituents=rows[2:],market_pe_ratio=1),{'2408'})
 def test_excess_growth_bellwether(self):
  a=kevin_calculate(BELLWETHER)
  self.assertAlmostEqual(a['eps'],46.33656,places=3);self.assertAlmostEqual(a['delta_pp'],108.9,places=1);self.assertEqual(a['branch'],'excess_growth')
  self.assertAlmostEqual(a['pe_conservative'],31.44,places=2);self.assertAlmostEqual(a['pe_optimistic'],43.81,places=2);self.assertAlmostEqual(a['model_value'],1743.3,places=1)
  self.assertNotIn('model_value_with_premium',a);self.assertFalse(a['low_base'])
 def test_premium_applies_to_target_not_eps(self):
  base=kevin_calculate(BELLWETHER); p=kevin_calculate({**BELLWETHER,'target_premium':1.5})
  self.assertAlmostEqual(p['eps'],base['eps']); self.assertAlmostEqual(p['growth'],base['growth']); self.assertAlmostEqual(p['model_value'],base['model_value'])
  self.assertAlmostEqual(p['model_value_with_premium'],2614.9,places=1)
 def test_eps_multiplier_rejected_with_migration_hint(self):
  with self.assertRaisesRegex(ValueError,'target_premium'): kevin_calculate({**BELLWETHER,'multiplier':1.5})
  self.assertAlmostEqual(kevin_calculate({**BELLWETHER,'multiplier':1})['model_value'],1743.3,places=1)
  with self.assertRaises(ValueError): kevin_calculate({**BELLWETHER,'target_premium':0})
 def test_below_hurdle_and_cycle_peak(self):
  slow=kevin_calculate({**BELLWETHER,'previous_eps':46.33656/1.256})
  self.assertEqual(slow['branch'],'below_anchor_growth');self.assertAlmostEqual(slow['pe_conservative'],17.76,places=2);self.assertAlmostEqual(slow['pe_optimistic'],20.9995,places=3)
  floor=kevin_calculate({**BELLWETHER,'previous_eps':46.33656/.2});self.assertAlmostEqual(floor['pe_conservative'],20.999471*.25)
  peak=kevin_calculate({**BELLWETHER,'price':300})
  self.assertEqual(peak['branch'],'cycle_peak_auto');self.assertAlmostEqual(peak['pe_conservative'],14.14,places=2);self.assertAlmostEqual(peak['effective_eps'],(46.33656+18)/2,places=3)
  with self.assertRaisesRegex(ValueError,'cycle_reason'):kevin_calculate({**BELLWETHER,'price':300,'cycle_peak':False})
  ok=kevin_calculate({**BELLWETHER,'price':300,'cycle_peak':False,'cycle_reason':'new capacity, verified'});self.assertEqual(ok['branch'],'excess_growth')
 def test_cap_200_and_low_base(self):
  hot=kevin_calculate({**BELLWETHER,'previous_eps':46.33656/15.11})
  self.assertTrue(hot['low_base']);self.assertEqual(hot['delta_capped_pp'],200);self.assertAlmostEqual(hot['pe_conservative'],20.999471+200**.5);self.assertAlmostEqual(hot['pe_optimistic'],20.999471+200**(2/3))
  self.assertTrue(any('excess cap' in w for w in kevin_calculate({**BELLWETHER,'excess_cap':100})['warnings']))
 def test_cpo_small_excess_and_leg_sorting(self):
  x=dict(revenue_ytd=952,months=12,consolidated_margin=.1,margin_basis='consolidated',owner_ratio=1,capital_thousands=100,par=10,previous_eps=6.14,price=286,**CPO)
  a=kevin_calculate(x);self.assertAlmostEqual(a['eps'],9.52);self.assertAlmostEqual(a['pe_conservative'],28.32,places=2);self.assertAlmostEqual(a['pe_optimistic'],28.52,places=2)
  near=kevin_calculate({**x,'previous_eps':9.52/1.533864})
  self.assertLess(near['delta_pp'],1);self.assertLessEqual(near['pe_conservative'],near['pe_optimistic']);self.assertTrue(any('sorted' in w for w in near['warnings']))
 def test_earnings_quality_levels(self):
  fuqiao=earnings_quality(dict(scope='consolidated',revenue=4012631,pretax=1498358,tax=197897,net_income=1300461,nonrecurring=dict(fvtpl=579850,fx=26509,disposals=-2)))
  self.assertEqual(fuqiao['level'],'choose'); self.assertAlmostEqual(fuqiao['core_margin'],.192938,places=5)
  self.assertAlmostEqual(earnings_quality(SONGCHUAN_H1)['core_margin'],.0947128,places=6)
  self.assertEqual(earnings_quality(dict(scope='consolidated',revenue=1167115,pretax=189072,tax=36980,net_income=152092,nonrecurring=dict(fx=12601)))['level'],'warn')
  self.assertEqual(earnings_quality(dict(scope='consolidated',revenue=165658435,pretax=24930070,tax=5549864,net_income=19380206,nonrecurring=dict(fx=132793,fvtpl=5829)))['level'],'clean')
 def test_earnings_quality_requires_consolidated_and_itemized(self):
  with self.assertRaises(ValueError): earnings_quality({**SONGCHUAN_H1,'scope':'parent_attributable'})
  with self.assertRaises(ValueError): earnings_quality({**SONGCHUAN_H1,'nonrecurring':52237})
 def test_choice_required_at_ten_percent(self):
  with self.assertRaisesRegex(ValueError,'margin_choice'): kevin_valuation({**SONGCHUAN,'previous_eps':4.75})
  with self.assertRaises(ValueError): kevin_valuation({**SONGCHUAN,'consolidated_margin':.1,'margin_basis':'consolidated','margin_choice':'core','previous_eps':4.75})
 def test_normalized_base_eps(self):
  v=kevin_valuation({**SONGCHUAN,'margin_choice':'core','previous_eps':4.75,'previous_eps_basis':'normalized','previous_eps_reported':3.63,'previous_eps_note':'2025Q2 FX loss restored'})
  self.assertAlmostEqual(v['model_value'],440.5,places=1); self.assertAlmostEqual(v['scenarios']['A']['growth_vs_reported_eps'],1.9459,places=3)
  self.assertAlmostEqual(kevin_valuation({**SONGCHUAN,'margin_choice':'core','previous_eps':3.63})['model_value'],513.4,places=1)
  with self.assertRaisesRegex(ValueError,'previous_eps_note'): kevin_valuation({**SONGCHUAN,'margin_choice':'core','previous_eps':4.75,'previous_eps_basis':'normalized','previous_eps_reported':3.63})
 def test_run_rate_scenario_b(self):
  v=kevin_valuation({**SONGCHUAN,'margin_choice':'core','previous_eps':4.75,'run_rate':dict(recent_months=[986396,872043],earnings_quality=SONGCHUAN_Q2,margin_period='2026Q2',inorganic_monthly=53228,pull_in_suspected=True)})
  b=v['scenarios']['B']; self.assertAlmostEqual(b['annual_revenue'],9692140); self.assertAlmostEqual(b['eps'],13.5787,places=3); self.assertAlmostEqual(b['model_value'],641.5,places=1)
  self.assertAlmostEqual(v['b_vs_a'],641.5/440.5-1,places=2); self.assertEqual(len(v['flags']),2); self.assertAlmostEqual(b['inorganic_share_of_recent'],.0573,places=3)
  with self.assertRaises(ValueError): kevin_valuation({**SONGCHUAN,'margin_choice':'core','previous_eps':4.75,'run_rate':dict(recent_months=[986396],consolidated_margin=.11,margin_basis='consolidated')})
 def test_run_rate_not_applicable_isolated(self):
  v=kevin_valuation({**BELLWETHER,'run_rate':dict(recent_months=[100,100],consolidated_margin=-.01,margin_basis='consolidated')})
  self.assertEqual(v['scenarios']['B']['status'],'not_applicable'); self.assertNotIn('b_vs_a',v); self.assertAlmostEqual(v['model_value'],1743.3,places=1)

if __name__=='__main__': unittest.main(verbosity=2)
