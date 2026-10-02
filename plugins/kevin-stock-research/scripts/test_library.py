import io, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import pypdfium2 as pdfium
from research import Store, LAYOUT, read
from workflow import onboard
from library import (CATEGORIES, PLACEHOLDER, parse_mops, parse_canonical, validate_entry, build_name, short_name,
                     key_from_name, classify, Known, dedupe_check)
from mops import pending

MOPS='https://doc.twse.com.tw/server-java/t57sb01?step=9&kind={kind}&co_id=6739&filename={name}'
def pdf(width=595,pages=1):
    doc=pdfium.PdfDocument.new()
    for _ in range(pages): doc.new_page(width,842)
    buf=io.BytesIO(); doc.save(buf); doc.close(); return buf.getvalue()

class NamingTests(unittest.TestCase):
    def test_mops_codes(self):
        self.assertEqual(parse_mops('202504_6739_AI1_20260508_123130.pdf')['category'],'02_年度財報')
        self.assertEqual(parse_mops('202504_6739_AI1.pdf')['label'],'2025')
        q2=parse_mops('202502_6739_AI1.pdf');self.assertEqual((q2['category'],q2['label']),('03_季報','2025Q2'));self.assertIn('累計',q2['title'])
        self.assertEqual(parse_mops('202501_6739_AI1.pdf')['title'],'合併季報_第一季')
        ar=parse_mops('2025_6739_20260527F04_20260508_123011.pdf')
        self.assertEqual((ar['category'],ar['label'],ar['language'],ar['meeting_date']),('01_年報','2025','中文','2026-05-27'))
        self.assertEqual(parse_mops('2022_3653_20230616FE4.pdf')['language'],'英文')
        self.assertIn('warning',parse_mops('2025_6739_20250527F04.pdf'))
        self.assertIsNone(parse_mops('202504_6739_AI9.pdf'));self.assertIsNone(parse_mops('report.pdf'))
    def entry(self,**kw):return {'category':'03_季報','label':'2025Q1','title':'合併季報_第一季','language':'中文','publisher':'竹陞',**kw}
    def test_period_rules(self):
        validate_entry(self.entry())
        for bad in (dict(label='2025Q4',title='合併季報'),dict(label='2025Q2',title='合併季報'),dict(label='2025'),
                    dict(category='02_年度財報',label='2025',title='Q4合併財報'),dict(category='01_年報',label='2025-05-27',title='年報'),
                    dict(category='04_法說會資料',label='20260909',title='法人說明會簡報'),dict(language='日文'),dict(category='09_其他')):
            with self.assertRaises(ValueError,msg=bad):validate_entry(self.entry(**bad))
        validate_entry(self.entry(category='04_法說會資料',label='2026-09-09',title='法人說明會簡報'))
    def test_names(self):
        e=self.entry(category='01_年報',label='2025',title='年報')
        self.assertEqual(build_name(e,'6739','竹陞'),'竹陞_6739_2025_年報_中文.pdf')
        ext=self.entry(category='06_券商研究',label='2025-10-27',title='AI伺服器 液冷/滲透率',publisher='凱基')
        self.assertEqual(build_name(ext,'6739','竹陞'),'凱基_2025-10-27_AI伺服器-液冷-滲透率_中文.pdf')
        self.assertEqual(build_name({**e,'variant':'01405587'},'6739','竹陞'),'竹陞_6739_2025_年報_中文_來源版01405587.pdf')
        c=parse_canonical('健策_3653_2023_年報_英文_來源版01405587.pdf');self.assertEqual((c['ticker'],c['label'],c['variant']),('3653','2023','01405587'))
        self.assertEqual(parse_canonical('竹陞_6739_2025Q2_合併季報_含上半年累計_中文.pdf')['title'],'合併季報_含上半年累計')
        self.assertEqual(short_name({'name':'竹陞科技'}),'竹陞');self.assertEqual(short_name({'name':'健策精密'}),'健策');self.assertEqual(short_name({'name':'X','short_name':'Y'}),'Y')
    def test_document_key_bridges_mops_and_canonical_names(self):
        self.assertEqual(key_from_name('2025_6739_20260527F04.pdf','6739'),key_from_name('竹陞_6739_2025_年報_中文.pdf','6739'))
        self.assertEqual(key_from_name('202504_6739_AI1.pdf','6739'),key_from_name('竹陞_6739_2025_年度合併財報_中文.pdf','6739'))
        self.assertNotEqual(key_from_name('2025_6739_20260527FE4.pdf','6739'),key_from_name('竹陞_6739_2025_年報_中文.pdf','6739'))
        self.assertIsNone(key_from_name('2025_3653_20260527F04.pdf','6739'))

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'TPEX-6739'
        self.c=onboard(self.root,'TPEX','6739','竹陞科技','semiconductor');self.s=Store(self.root)
    def tearDown(self):self.s.db.close();self.tmp.cleanup()
    def add(self,blob,name,kind='A'):
        return self.s.ingest(blob,security='TPEX:6739',category='mops',url=MOPS.format(kind=kind,name=name),suffix='.pdf')
    def test_layout_and_onboard_files(self):
        for f in LAYOUT:self.assertTrue((self.root/f).is_dir(),f)
        self.assertEqual([p.split('/')[1] for p in LAYOUT if p.startswith('分類PDF/')],list(CATEGORIES))
        self.assertTrue((self.root/'README.md').exists());self.assertEqual(read(self.root/'缺口清單.json')['gaps'],[])
    def test_dry_run_writes_nothing(self):
        self.add(pdf(),'202504_6739_AI1.pdf')
        r=classify(self.s,self.c)
        self.assertEqual(r['status'],'dry_run');self.assertEqual(r['counts']['02_年度財報'],1)
        self.assertEqual(list((self.root/'分類PDF').rglob('*.pdf')),[]);self.assertFalse((self.root/'分類PDF/PDF分類索引.json').exists())
    def test_apply_hardlinks_dedupes_and_indexes(self):
        ar=pdf(600,3)
        self.add(ar,'2025_6739_20260527F04.pdf','F');self.add(ar,'2025_6739_20260527F04_20260508_123011.pdf','F')
        self.add(pdf(601),'202504_6739_AI1.pdf');self.add(pdf(602),'202502_6739_AI1.pdf');self.add(pdf(603),'202604_3653_AI1.pdf')
        r=classify(self.s,self.c,apply=True)
        self.assertEqual(r['counts'],{'01_年報':1,'02_年度財報':1,'03_季報':1,'04_法說會資料':0,'05_技術簡報':0,'06_券商研究':0,'07_產業資料':0,'08_股東會與公司治理':0})
        target=self.root/'分類PDF/01_年報/竹陞_6739_2025_年報_中文.pdf'
        self.assertTrue(target.exists())
        idx=read(self.root/'分類PDF/PDF分類索引.json');rec=[f for f in idx['files'] if f['category']=='01_年報'][0]
        self.assertEqual(rec['pages'],3);self.assertEqual(rec['storage'],'hardlink');self.assertEqual(len(rec['source_urls']),2);self.assertEqual(rec['date_meaning'],'會計年度')
        self.assertEqual(target.stat().st_ino,(self.root/rec['original_path']).stat().st_ino)
        self.assertTrue((self.root/'分類PDF/03_季報/竹陞_6739_2025Q2_合併季報_含上半年累計_中文.pdf').exists())
        self.assertIn('累計',[f for f in idx['files'] if f['category']=='03_季報'][0]['note'])
        self.assertEqual(len(idx['unclassified']),1);self.assertIn('3653',idx['unclassified'][0]['reason'])
        self.assertTrue((self.root/'分類PDF/04_法說會資料'/PLACEHOLDER).exists());self.assertFalse((self.root/'分類PDF/01_年報'/PLACEHOLDER).exists())
        for f in ('PDF分類索引.xlsx','PDF分類目錄.html','整理說明.md'):self.assertTrue((self.root/'分類PDF'/f).exists(),f)
        again=classify(self.s,self.c,apply=True)
        self.assertEqual(again['actions'],[]);self.assertEqual(len(list((self.root/'分類PDF').rglob('*.pdf'))),3)
    def test_same_title_different_bytes_all_get_source_code(self):
        a,b=pdf(610),pdf(611)
        self.add(a,'2023_6739_20240530FE4.pdf','F')
        self.s.ingest(b,security='TPEX:6739',category='ir',url='https://ir.example.test/ar2023_en.pdf',suffix='.pdf')
        r=classify(self.s,self.c,[{'original_filename':'ar2023_en.pdf','category':'01_年報','label':'2023','title':'年報','language':'英文'}],apply=True)
        names=sorted(p.name for p in (self.root/'分類PDF/01_年報').glob('*.pdf'))
        self.assertEqual(len(names),2);self.assertTrue(all('_來源版' in n for n in names),names)
        self.assertEqual(r['counts']['01_年報'],2)
    def test_existing_library_file_kept_and_not_duplicated(self):
        blob=pdf(620);d=self.root/'分類PDF/02_年度財報';(d/'竹陞_6739_2025_年度合併財報_中文.pdf').write_bytes(blob)
        self.add(blob,'202504_6739_AI1_20260508_123130.pdf')
        r=classify(self.s,self.c,apply=True)
        self.assertEqual(r['actions'],[]);self.assertEqual(len(list(d.glob('*.pdf'))),1)
        rec=read(self.root/'分類PDF/PDF分類索引.json')['files'][0];self.assertEqual(rec['storage'],'existing');self.assertEqual(len(rec['source_urls']),1)
    def test_misfiled_existing_file_reported_not_moved(self):
        blob=pdf(640);d=self.root/'分類PDF/03_季報';(d/'竹陞_6739_2025_年度合併財報_中文.pdf').write_bytes(blob)
        self.add(blob,'202504_6739_AI1.pdf')
        r=classify(self.s,self.c,apply=True)
        self.assertEqual(r['conflicts'][0]['computed_category'],'02_年度財報');self.assertEqual(r['counts']['03_季報'],1);self.assertEqual(r['counts']['02_年度財報'],0)
        self.assertTrue((d/'竹陞_6739_2025_年度合併財報_中文.pdf').exists())
    def test_unknown_requires_manifest(self):
        self.s.ingest(pdf(630),security='TPEX:6739',category='broker',url='https://broker.example.test/x.pdf',suffix='.pdf')
        self.assertEqual(len(classify(self.s,self.c)['unclassified']),1)
        r=classify(self.s,self.c,[{'original_filename':'x.pdf','category':'06_券商研究','label':'2026-09-15','title':'首次評等','publisher':'某券商'}],apply=True)
        self.assertTrue((self.root/'分類PDF/06_券商研究/某券商_2026-09-15_首次評等_中文.pdf').exists())
        with self.assertRaises(ValueError):classify(self.s,self.c,[{'original_filename':'nope.pdf','category':'06_券商研究'}])

class PreDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'r'
        self.c=onboard(self.root,'TPEX','6739','竹陞科技');self.s=Store(self.root)
        (self.root/'分類PDF/01_年報/竹陞_6739_2025_年報_中文.pdf').write_bytes(pdf())
    def tearDown(self):self.s.db.close();self.tmp.cleanup()
    def test_known_annual_report_skipped(self):
        k=Known(self.s,self.c)
        self.assertIn('already held',k.has('2025_6739_20260527F04.pdf'))
        self.assertIsNone(k.has('2024_6739_20250527F04.pdf'));self.assertIsNone(k.has('2025_6739_20260527FE4.pdf'))
        todo,skip=pending([{'filename':'2025_6739_20260527F04.pdf'},{'filename':'2024_6739_20250527F04.pdf'}],k)
        self.assertEqual([r['filename'] for r in todo],['2024_6739_20250527F04.pdf']);self.assertEqual(len(skip),1)
    def test_drive_listing_counts_as_held(self):
        drive={'files':[{'title':'202602_6739_AI1_20260826_205211.pdf'}]}
        r=dedupe_check(self.s,self.c,[{'url':MOPS.format(kind='A',name='202602_6739_AI1.pdf')},{'url':MOPS.format(kind='A',name='202601_6739_AI1.pdf')}],drive)
        self.assertEqual([x['checked_name'] for x in r['skip']],['202602_6739_AI1.pdf']);self.assertEqual(len(r['download']),1)
    def test_ingest_skips_held_without_fetch(self):
        manifest=Path(self.tmp.name)/'m.json'
        manifest.write_text(json.dumps([{'security':'TPEX:6739','category':'annual','url':MOPS.format(kind='F',name='2025_6739_20260527F04.pdf'),'suffix':'.pdf'}]),encoding='utf-8')
        out=subprocess.run([sys.executable,str(Path(__file__).with_name('workflow.py')),'--root',str(self.root),'ingest','--manifest',str(manifest)],capture_output=True,text=True,check=True)
        r=json.loads(out.stdout);self.assertEqual(r['evidence_ids'],[]);self.assertEqual(len(r['skipped_already_held']),1)

if __name__=='__main__':unittest.main()
