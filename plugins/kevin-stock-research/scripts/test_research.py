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
  x={'revenue_ytd':800,'months':8,'consolidated_margin':.25,'owner_ratio':.9,'capital_thousands':100,'par':10,'previous_eps':20,'base_pe':10,'etf_growth_fy':.2,'margin_basis':'consolidated'}
  self.assertAlmostEqual(kevin_calculate(x)['eps'],27)
  with self.assertRaises(ValueError):kevin_calculate({**x,'margin_basis':'parent'})
  with self.assertRaises(ValueError):kevin_calculate({**x,'previous_eps':0})
  self.assertEqual(kevin_calculate({**x,'previous_eps':40})['branch'],'below_etf_growth')
  legacy={k:v for k,v in x.items() if k not in ('base_pe','etf_growth_fy')}|{'anchor_method':'legacy_dual_anchor','base_pe_p':10,'base_pe_q':8}
  with self.assertRaises(ValueError):kevin_calculate({**legacy,'previous_eps':40})
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

# Kevin 回歸案例：數字取自公開財報（2026H1／1-8月營收）與 2026-09／2026-10 workbook 驗算結果；非研究結論、非投資建議。
# 0.2.1–0.7.0 雙層錨定（legacy_dual_anchor）只供重現舊 workbook。
LEGACY=dict(anchor_method='legacy_dual_anchor')
BELLWETHER_CORE=dict(revenue_ytd=6811534,months=8,consolidated_margin=1475886/5037705,margin_basis='consolidated',owner_ratio=1,capital_thousands=646000,par=10,previous_eps=18)
BELLWETHER=dict(BELLWETHER_CORE,**LEGACY,base_pe_p=14.025,base_pe_q=10.285)
SONGCHUAN_H1=dict(scope='consolidated',revenue=4117008,pretax=585489,tax=147119,net_income=438370,nonrecurring=dict(fx=52237,disposals=12601,fvtpl=-146))
SONGCHUAN_Q2=dict(scope='consolidated',revenue=2259879,pretax=356148,tax=94262,net_income=261886,nonrecurring=dict(disposals=7453,fx=7030,fvtpl=-137))
SONGCHUAN_CORE=dict(revenue_ytd=5975262,months=8,owner_ratio=440369/438370,nci_loss_verified=True,capital_thousands=797460,par=10,earnings_quality=SONGCHUAN_H1)
SONGCHUAN=dict(SONGCHUAN_CORE,**LEGACY,base_pe_p=23.8425,base_pe_q=17.391)
class KevinModelTests(unittest.TestCase):
 """legacy_dual_anchor：0.2.1–0.7.0 數值必須維持可重現。"""
 def test_anchor_three_categories(self):
  for etf,rp,rq,p,q in ((22,.75,.55,14.025,10.285),(28,.85,.62,20.23,14.756),(33,.85,.62,23.8425,17.391)):
   b=anchor_bases(dict(LEGACY,etf_pe=etf,ratio_p=rp,ratio_q=rq,market_pe=31.26,market_median_pe=17))
   self.assertEqual(b['m_adj'],.85); self.assertAlmostEqual(b['base_pe_p'],p); self.assertAlmostEqual(b['base_pe_q'],q)
 def test_anchor_m_adj_boundaries(self):
  m=lambda mp:anchor_bases(dict(LEGACY,etf_pe=20,ratio_p=1,ratio_q=1,market_pe=mp,market_median_pe=10))['m_adj']
  self.assertEqual(m(13),1.0); self.assertEqual(m(13.1),.85); self.assertEqual(m(8),1.0); self.assertEqual(m(7.9),1.15)
  with self.assertRaises(ValueError): anchor_bases(dict(LEGACY,etf_pe=0,ratio_p=1,ratio_q=1,market_pe=10,market_median_pe=10))
 def test_premium_applies_to_target_not_eps(self):
  base=kevin_calculate(BELLWETHER); self.assertAlmostEqual(base['model_value'],1529.39,places=1); self.assertNotIn('model_value_with_premium',base)
  p=kevin_calculate({**BELLWETHER,'target_premium':1.5})
  self.assertAlmostEqual(p['eps'],base['eps']); self.assertAlmostEqual(p['growth'],base['growth']); self.assertAlmostEqual(p['model_value'],base['model_value'])
  self.assertAlmostEqual(p['model_value_with_premium'],2294.08,places=1)
 def test_eps_multiplier_rejected_with_migration_hint(self):
  with self.assertRaisesRegex(ValueError,'target_premium'): kevin_calculate({**BELLWETHER,'multiplier':1.5})
  self.assertAlmostEqual(kevin_calculate({**BELLWETHER,'multiplier':1})['model_value'],1529.39,places=1)
  with self.assertRaises(ValueError): kevin_calculate({**BELLWETHER,'target_premium':0})
 def test_old_base_names_rejected(self):
  with self.assertRaisesRegex(ValueError,'base_pe_p'): kevin_calculate({**BELLWETHER,'base_pe_low':14.025})
  with self.assertRaisesRegex(ValueError,'base_pe_q'): kevin_calculate({**BELLWETHER,'base_pe_high':10.285})
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
  self.assertAlmostEqual(v['model_value'],414.04,places=1); self.assertAlmostEqual(v['scenarios']['A']['growth_vs_reported_eps'],1.9459,places=3)
  self.assertAlmostEqual(kevin_valuation({**SONGCHUAN,'margin_choice':'core','previous_eps':3.63})['model_value'],474.60,places=1)
  with self.assertRaisesRegex(ValueError,'previous_eps_note'): kevin_valuation({**SONGCHUAN,'margin_choice':'core','previous_eps':4.75,'previous_eps_basis':'normalized','previous_eps_reported':3.63})
 def test_run_rate_scenario_b(self):
  v=kevin_valuation({**SONGCHUAN,'margin_choice':'core','previous_eps':4.75,'run_rate':dict(recent_months=[986396,872043],earnings_quality=SONGCHUAN_Q2,margin_period='2026Q2',inorganic_monthly=53228,pull_in_suspected=True)})
  b=v['scenarios']['B']; self.assertAlmostEqual(b['annual_revenue'],9692140); self.assertAlmostEqual(b['eps'],13.5787,places=3); self.assertAlmostEqual(b['model_value'],593.63,places=1)
  self.assertAlmostEqual(v['b_vs_a'],.4337,places=3); self.assertEqual(len(v['flags']),2); self.assertAlmostEqual(b['inorganic_share_of_recent'],.0573,places=3)
  with self.assertRaises(ValueError): kevin_valuation({**SONGCHUAN,'margin_choice':'core','previous_eps':4.75,'run_rate':dict(recent_months=[986396],consolidated_margin=.11,margin_basis='consolidated')})
 def test_run_rate_negative_growth_isolated(self):
  v=kevin_valuation({**BELLWETHER,'run_rate':dict(recent_months=[100,100],consolidated_margin=.01,margin_basis='consolidated')})
  self.assertEqual(v['scenarios']['B']['status'],'not_applicable'); self.assertNotIn('b_vs_a',v); self.assertAlmostEqual(v['model_value'],1529.39,places=1)
  self.assertEqual(v['model'],'kevin_dual_anchor_legacy'); self.assertTrue(any('legacy_dual_anchor' in w for w in v['warnings']))

# v3.7b（2026-10-03 收盤、ETF 持股 2026-08-31、剔除記憶體、M_adj 0.85；Kevin目標價_2026_09.xlsx「錨定ETF」）
V37B_ANCHORS={'portfolio':(29.229530,.183130,24.705260,20.999471,.485004),'cpo':(38.635243,.222976,31.591182,26.852505,.528864),'potential':(41.869429,.223364,34.224825,29.091102,.602024)}
HURDLE=.485004
BELL37=dict(BELLWETHER_CORE,base_pe=20.999471,etf_growth_fy=HURDLE,price=1165)
SONG37=dict(SONGCHUAN_CORE,base_pe=29.091102,etf_growth_fy=.602024,margin_choice='core')
# v3.7（0.8.0）重現：各類自身 G_FY 當門檻、上限 100
V37_OLD=dict(base_pe=20.748211,hurdle_growth=.511662,excess_cap=100)

class KevinV37Tests(unittest.TestCase):
 """v3.7b ETF 隱含成長錨定（0.8.1 預設：剔除記憶體、超額門檻＝類別 ETF 自身 G_FY、Δ 上限 200、低基期旗標）。"""
 def test_anchor_reference_values(self):
  for cat,(trailing,g_ttm,forward,b,g_fy) in V37B_ANCHORS.items():
   r=anchor_bases(dict(etf_pe_trailing=trailing,etf_growth_ttm=g_ttm,etf_growth_fy=g_fy,market_pe=31.26,market_median_pe=17))
   self.assertEqual(r['anchor_method'],'etf_implied_growth',cat); self.assertEqual(r['m_adj'],.85)
   self.assertAlmostEqual(r['etf_pe_forward'],forward,places=4); self.assertAlmostEqual(r['base_pe'],b,places=4); self.assertEqual(r['etf_growth_fy'],g_fy)
 def test_anchor_profile_matches_reference(self):
  prof=json.loads((Path(__file__).resolve().parents[1]/'profiles/anchors.json').read_text(encoding='utf-8'))
  self.assertEqual(prof['method'],'etf_implied_growth'); self.assertEqual(prof['model_version'],'v3.7b'); self.assertEqual(prof['latest_known']['asof'],'2026-10-03')
  self.assertIn('記憶體',prof['excluded_themes']); self.assertEqual(len(prof['excluded_codes']),21); self.assertIn('2408',prof['excluded_codes']); self.assertIn('2344',prof['excluded_codes'])
  self.assertNotIn('hurdle',prof); self.assertEqual(prof['hurdle_rule'],'category_etf_growth_fy'); self.assertEqual(prof['excess_cap'],200)
  for cat,(trailing,g_ttm,forward,b,g_fy) in V37B_ANCHORS.items():
   k=prof['categories'][cat]['latest_known']; self.assertNotIn('ratio_p',prof['categories'][cat])
   self.assertEqual((k['etf_pe_trailing'],k['etf_growth_ttm'],k['base_pe'],k['etf_growth_fy'],k['hurdle_growth']),(trailing,g_ttm,b,g_fy,g_fy))
  self.assertEqual([prof['categories'][c]['latest_known']['excluded_count'] for c in ('portfolio','cpo','potential')],[1,2,2])
 def test_anchor_direct_base_and_conflicts(self):
  self.assertEqual(anchor_bases(dict(base_pe=20.999471,hurdle_growth=HURDLE))['base_pe_source'],'direct')
  self.assertEqual(anchor_bases(dict(base_pe=20.999471,etf_growth_fy=HURDLE))['base_pe_source'],'direct')
  with self.assertRaises(ValueError): anchor_bases(dict(base_pe=20,etf_pe_trailing=29,etf_growth_ttm=.19,etf_growth_fy=.5))
  with self.assertRaises(ValueError): anchor_bases(dict(etf_pe_trailing=29,etf_growth_ttm=.19,market_pe=31,market_median_pe=17))  # G_FY 或門檻必填
  with self.assertRaises(ValueError): anchor_bases(dict(etf_pe_trailing=29,etf_growth_ttm=-1,etf_growth_fy=.5,market_pe=31,market_median_pe=17))
  with self.assertRaises(ValueError): anchor_bases(dict(base_pe=20,hurdle_growth=-1))
  with self.assertRaisesRegex(ValueError,'v3.7'): anchor_bases(dict(etf_pe=22,ratio_p=.75,ratio_q=.55,market_pe=31.26,market_median_pe=17))
 def test_bellwether_v37b(self):
  r=kevin_calculate(BELL37)
  self.assertEqual(r['model_version'],'v3.7b'); self.assertEqual(r['hurdle_source'],'etf_growth_fy'); self.assertEqual(r['delta_cap'],200)
  self.assertAlmostEqual(r['eps'],46.34,places=2); self.assertAlmostEqual(r['growth'],1.5743,places=3)
  self.assertAlmostEqual(r['delta'],108.9,places=1); self.assertEqual(r['delta_capped'],r['delta']); self.assertEqual(r['branch'],'excess_growth'); self.assertFalse(r['peak_earnings']); self.assertFalse(r['low_base'])
  self.assertAlmostEqual(r['pe_cons'],31.44,places=2); self.assertAlmostEqual(r['pe_opt'],43.81,places=2)
  self.assertAlmostEqual(r['model_value'],1743,delta=1); self.assertAlmostEqual(r['price_cons'],r['eps']*r['pe_cons']); self.assertNotIn('model_value_with_premium',r)
  self.assertNotIn('pe_p',r)
 def test_bellwether_premium_on_target_only(self):
  base=kevin_calculate(BELL37); p=kevin_calculate({**BELL37,'target_premium':1.5})
  self.assertAlmostEqual(p['eps'],base['eps']); self.assertAlmostEqual(p['model_value'],base['model_value']); self.assertAlmostEqual(p['model_value_with_premium'],2615,delta=1)
  with self.assertRaisesRegex(ValueError,'target_premium'): kevin_calculate({**BELL37,'multiplier':1.5})
 def test_songchuan_three_cases(self):
  a=kevin_valuation({**SONG37,'previous_eps':4.75})['scenarios']['A']
  self.assertAlmostEqual(a['eps'],10.69,places=2); self.assertAlmostEqual(a['growth'],1.2513,delta=.002); self.assertAlmostEqual(a['delta'],64.9,delta=.1)
  self.assertAlmostEqual(a['pe_cons'],37.15,delta=.01); self.assertAlmostEqual(a['pe_opt'],45.25,delta=.02); self.assertAlmostEqual(a['model_value'],440.5,delta=1)
  c=kevin_valuation({**SONG37,'previous_eps':3.63})['scenarios']['A']
  self.assertAlmostEqual(c['delta'],134.4,delta=.1); self.assertEqual(c['delta_capped'],c['delta']); self.assertAlmostEqual(c['pe_cons'],40.68,delta=.01); self.assertAlmostEqual(c['pe_opt'],55.33,delta=.02); self.assertAlmostEqual(c['model_value'],513,delta=1)
  v=kevin_valuation({**SONG37,'previous_eps':4.75,'run_rate':dict(recent_months=[986396,872043],earnings_quality=SONGCHUAN_Q2,margin_period='2026Q2')})
  b=v['scenarios']['B']; self.assertAlmostEqual(b['eps'],13.58,places=2); self.assertAlmostEqual(b['delta'],125.7,delta=.1); self.assertAlmostEqual(b['model_value'],641.5,delta=1)
  self.assertEqual(v['model'],'kevin_v3_7_etf_implied_growth'); self.assertEqual(v['model_version'],'v3.7b'); self.assertTrue(any('peak-earnings check' in w for w in v['warnings']))
 def test_reference_checks(self):
  q=kevin_calculate(dict(BELL37,revenue_ytd=1,months=12,consolidated_margin=1,capital_thousands=1,par=92.722,previous_eps=49.17,price=3510,target_premium=1.5))
  self.assertAlmostEqual(q['eps'],92.722); self.assertAlmostEqual(q['pe_cons'],27.33,places=2); self.assertAlmostEqual(q['pe_opt'],32.71,places=2)
  self.assertAlmostEqual(q['model_value_with_premium'],92.722*(27.33+32.71)/2*1.5,delta=1)
  unit=dict(revenue_ytd=1,months=12,consolidated_margin=1,margin_basis='consolidated',owner_ratio=1,capital_thousands=1,par=1,etf_growth_fy=HURDLE)
  w=kevin_calculate(dict(unit,base_pe=20.999471,previous_eps=1/1.256,price=100))
  self.assertEqual(w['branch'],'below_etf_growth'); self.assertAlmostEqual(w['pe_cons'],17.76,places=2); self.assertAlmostEqual(w['pe_opt'],21.00,places=2)
  s=kevin_calculate(dict(unit,base_pe=26.852505,etf_growth_fy=.528864,par=1.551,previous_eps=1,price=100))
  self.assertAlmostEqual(s['delta'],2.21,places=2); self.assertAlmostEqual(s['pe_cons'],28.34,places=2); self.assertAlmostEqual(s['pe_opt'],28.55,places=2)
  l=kevin_calculate(dict(unit,base_pe=20.999471,par=15.11,previous_eps=1,price=1000))
  self.assertEqual(l['delta_capped'],200); self.assertAlmostEqual(l['pe_cons'],35.14,places=2); self.assertAlmostEqual(l['pe_opt'],55.20,places=2); self.assertTrue(l['low_base'])
 def test_low_base_flag(self):
  unit=dict(revenue_ytd=1,months=12,consolidated_margin=1,margin_basis='consolidated',owner_ratio=1,capital_thousands=1,base_pe=20.999471,etf_growth_fy=HURDLE)
  self.assertFalse(kevin_calculate(dict(unit,par=4,previous_eps=1,price=100))['low_base'])   # 剛好 300%
  self.assertTrue(kevin_calculate(dict(unit,par=4.01,previous_eps=1,price=100))['low_base'])
  self.assertFalse(kevin_calculate(dict(unit,par=10,previous_eps=1,price=50))['low_base'])   # 景氣高峰不標
  v=kevin_valuation(dict(unit,par=15.11,previous_eps=1,price=1000,margin_choice=None))
  self.assertTrue(any(f.startswith('scenario A: 低基期：預期 EPS 成長 1411%') and '剔除或改用兩年平均 EPS' in f for f in v['flags']))
 def test_below_hurdle(self):
  eps=kevin_calculate(BELL37)['eps']; r=kevin_calculate({**BELL37,'previous_eps':eps/1.256})
  self.assertAlmostEqual(r['growth'],.256); self.assertEqual(r['branch'],'below_etf_growth'); self.assertLess(r['delta'],0)
  self.assertAlmostEqual(r['pe_cons'],20.999471*1.256/(1+HURDLE),places=6); self.assertAlmostEqual(r['pe_cons'],17.76,places=2); self.assertAlmostEqual(r['pe_opt'],20.999471)
  floor=kevin_calculate({**BELL37,'previous_eps':eps/.2})  # g = -80% → 折減下限 0.25
  self.assertAlmostEqual(floor['pe_cons'],20.999471*.25)
 def test_peak_earnings(self):
  r=kevin_calculate({**BELL37,'price':300}); eps=r['eps']
  self.assertTrue(r['peak_earnings']); self.assertEqual(r['branch'],'peak_earnings'); self.assertEqual(r['growth_used'],0); self.assertIsNone(r['delta']); self.assertFalse(r['low_base'])
  self.assertAlmostEqual(r['pe_cons'],14.14,places=2); self.assertAlmostEqual(r['pe_opt'],20.999471/(1+HURDLE))
  self.assertAlmostEqual(r['eps_valuation'],(eps+18)/2); self.assertAlmostEqual(r['model_value'],r['eps_valuation']*20.999471/(1+HURDLE))
  v=kevin_valuation({**BELL37,'price':300}); self.assertTrue(any('peak earnings' in f for f in v['flags']))
  self.assertFalse(kevin_calculate({**BELL37,'price':8*eps})['peak_earnings'])  # 剛好 8 倍不算高峰
 def test_cpo_uses_own_gfy_and_override(self):
  x=dict(BELLWETHER_CORE,base_pe=26.852505,etf_growth_fy=.528864,price=1165)
  r=kevin_calculate(x); self.assertAlmostEqual(r['delta'],(r['growth']-.528864)*100); self.assertEqual(r['hurdle_growth'],.528864); self.assertEqual(r['hurdle_source'],'etf_growth_fy')
  o=kevin_valuation({**x,'hurdle_growth':HURDLE})
  self.assertEqual(o['scenarios']['A']['hurdle_source'],'hurdle_growth_override'); self.assertAlmostEqual(o['scenarios']['A']['delta'],(r['growth']-HURDLE)*100)
  self.assertTrue(any('hurdle_growth override' in w for w in o['warnings']))
  self.assertFalse(any('override' in w for w in kevin_valuation(x)['warnings']))
  with self.assertRaisesRegex(ValueError,'etf_growth_fy'): kevin_calculate({k:v for k,v in x.items() if k!='etf_growth_fy'})
 def test_cap_override_and_v37_reproduction(self):
  r=kevin_calculate(dict(BELLWETHER_CORE,**V37_OLD,price=1165))
  self.assertEqual(r['delta_cap'],100); self.assertEqual(r['delta_capped'],100); self.assertAlmostEqual(r['model_value'],1692,delta=1)
  v=kevin_valuation(dict(BELLWETHER_CORE,**V37_OLD,price=1165)); self.assertTrue(any('excess_cap overridden' in w for w in v['warnings']))
  with self.assertRaises(ValueError): kevin_calculate({**BELL37,'excess_cap':0})
 def test_old_fields_require_legacy_flag(self):
  with self.assertRaisesRegex(ValueError,'legacy_dual_anchor'): kevin_calculate(dict(BELLWETHER_CORE,base_pe_p=14.025,base_pe_q=10.285))
  with self.assertRaisesRegex(ValueError,'v3.7'): kevin_valuation(dict(SONGCHUAN_CORE,margin_choice='core',previous_eps=4.75,base_pe_p=23.8425,base_pe_q=17.391))
  with self.assertRaises(ValueError): kevin_calculate({**BELL37,'anchor_method':'something_else'})
  with self.assertRaises(ValueError): kevin_calculate({k:v for k,v in BELL37.items() if k!='etf_growth_fy'})
 def test_legacy_reproduces_old_values(self):
  self.assertAlmostEqual(kevin_calculate(BELLWETHER)['model_value'],1529.39,places=1)
  self.assertAlmostEqual(kevin_calculate({**BELLWETHER,'target_premium':1.5})['model_value_with_premium'],2294.08,places=1)
  self.assertNotIn('hurdle_growth',kevin_calculate(BELLWETHER))
 def test_run_rate_negative_growth_now_priced(self):
  v=kevin_valuation({**BELL37,'run_rate':dict(recent_months=[100,100],consolidated_margin=.01,margin_basis='consolidated')})
  self.assertEqual(v['scenarios']['B']['branch'],'below_etf_growth'); self.assertIn('b_vs_a',v); self.assertAlmostEqual(v['model_value'],1743,delta=1)

if __name__=='__main__': unittest.main(verbosity=2)
