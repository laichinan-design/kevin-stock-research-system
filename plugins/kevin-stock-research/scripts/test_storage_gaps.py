import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from research import Store, read, dump
from workflow import onboard, validate_config
import storage, gaps, readme

MOPS='https://doc.twse.com.tw/server-java/t57sb01?step=9&kind={kind}&co_id=6739&filename={name}'
WF=str(Path(__file__).with_name('workflow.py'))
def cli(root,*args,check=True):
    r=subprocess.run([sys.executable,WF,'--root',str(root),*args],capture_output=True,text=True)
    if check and r.returncode: raise AssertionError(r.stderr)
    return json.loads(r.stdout) if r.returncode==0 else r

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name);self.root=self.d/'TPEX-6739'
        self.c=onboard(self.root,'TPEX','6739','竹陞科技','semiconductor')
    def tearDown(self):self.tmp.cleanup()
    def test_default_folder_and_validation(self):
        self.assertEqual(self.c['storage']['drive_folder'],'投資組合-台股/竹陞6739/竹陞6739研究')
        for bad in ('../x','/abs/x','D:/data/x'):
            with self.assertRaises(ValueError):storage.make_storage(self.c,bad)
        with self.assertRaises(ValueError):validate_config({**self.c,'storage':{'drive_folder':'../x'}})
    def test_connector_plan_record_and_pending(self):
        (self.root/'正式成果/報告.docx').write_bytes(b'PK binary')
        (self.root/'分類PDF/整理說明.md').write_text('小檔',encoding='utf-8')
        (self.root/'分類PDF/PDF分類索引.json').write_text(json.dumps({'x':'y'*200000}),encoding='utf-8')
        (self.root/'runs/abc').mkdir(parents=True);(self.root/'runs/abc/plan.json').write_text('{}',encoding='utf-8')
        p=storage.plan(self.root,self.c);via={i['path']:i['via'] for i in p['changed']}
        self.assertEqual(p['mode'],'connector');self.assertEqual(via['分類PDF/整理說明.md'],'connector')
        self.assertEqual(via['正式成果/報告.docx'],'manual');self.assertEqual(via['分類PDF/PDF分類索引.json'],'manual')
        self.assertNotIn('runs/abc/plan.json',via)
        self.assertEqual(storage.sync(self.root,self.c)['note'][:7],'dry-run');self.assertFalse((self.root/storage.PENDING).exists())
        storage.sync(self.root,self.c,apply=True);self.assertIn('正式成果/報告.docx',(self.root/storage.PENDING).read_text(encoding='utf-8'))
        n=len(storage.plan(self.root,self.c)['changed'])
        r=storage.record(self.root,self.c,['正式成果/報告.docx'],['FILEID1'],'manual')
        self.assertEqual(r['still_pending'],n-1)
        self.assertEqual(read(self.root/storage.RECORD)['files']['正式成果/報告.docx']['drive_file_id'],'FILEID1')
        (self.root/'正式成果/報告.docx').write_bytes(b'PK changed')
        changed={i['path']:i['status'] for i in storage.plan(self.root,self.c)['changed']}
        self.assertEqual(changed['正式成果/報告.docx'],'modified')
        rep={i['path']:i.get('replace_drive_file_id') for i in storage.plan(self.root,self.c)['changed']}
        self.assertEqual(rep['正式成果/報告.docx'],'FILEID1')
        with self.assertRaises(ValueError):storage.record(self.root,self.c,['runs/abc/plan.json'])
    def test_local_sync_copies_and_never_deletes(self):
        drive=self.d/'GDrive';drive.mkdir()
        c=cli(self.root,'set-storage','--local-sync-root',str(drive))['storage'];cfg={**self.c,'storage':c}
        (self.root/'整合簡報/deck.pptx').write_bytes(b'PK deck')
        self.assertEqual(storage.plan(self.root,cfg)['mode'],'local_sync')
        r=storage.sync(self.root,cfg,apply=True);target=drive/'投資組合-台股/竹陞6739/竹陞6739研究'
        self.assertEqual((target/'整合簡報/deck.pptx').read_bytes(),b'PK deck');self.assertTrue((target/'README.md').exists())
        again=storage.plan(self.root,cfg);self.assertEqual(again['changed'],[]);self.assertGreater(again['unchanged'],0)
        (self.root/'整合簡報/deck.pptx').unlink()
        self.assertIn('整合簡報/deck.pptx',storage.plan(self.root,cfg)['removed_locally']);self.assertTrue((target/'整合簡報/deck.pptx').exists())
        moved={**cfg,'storage':{**c,'drive_folder':'投資組合-台股/其他'}}
        self.assertEqual(storage.plan(self.root,moved)['unchanged'],0)

class GapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'TPEX-6739'
        self.c=onboard(self.root,'TPEX','6739','竹陞科技','semiconductor');self.s=Store(self.root)
    def tearDown(self):self.s.db.close();self.tmp.cleanup()
    def test_expected_deadlines(self):
        labels=[(e['category'],e['label']) for e in gaps.expected('2026-10-02','6739',years=1)]
        self.assertEqual(sorted(labels),sorted([('02_年度財報','2025'),('01_年報','2025'),('03_季報','2025Q1'),('03_季報','2025Q2'),('03_季報','2025Q3'),('03_季報','2026Q1'),('03_季報','2026Q2')]))
        self.assertNotIn(('03_季報','2026Q3'),labels)
        self.assertNotIn(('01_年報','2025'),[(e['category'],e['label']) for e in gaps.expected('2026-06-29','6739',years=1)])
    def test_refresh_preserves_manual_and_skips_held(self):
        dump(self.root/'缺口清單.json',{'security':'TPEX:6739','gaps':[{'id':'concall','item':'法說簡報','need':'MOPS'}]})
        (self.root/'分類PDF/01_年報/竹陞_6739_2025_年報_中文.pdf').write_bytes(b'%PDF-1.4 fixture')
        self.s.ingest(None,security='TPEX:6739',category='mops',url=MOPS.format(kind='A',name='202602_6739_AI1.pdf'),title='2026Q2',status='blocked',note='HTTP 403')
        gaps.coverage_set(self.root,self.c,'2025 年報','1-76',101,'77-101','Drive 轉文字截斷')
        r=gaps.refresh(self.s,self.c,'2026-10-02',years=1)
        data=read(self.root/'缺口清單.json');ids={g['id'] for g in data['gaps']}
        self.assertIn('concall',ids);self.assertIn('identity',ids);self.assertNotIn('mops-F04-2025',ids);self.assertIn('mops-AI1-2026Q1',ids)
        self.assertEqual(r['blocked_sources'],1);self.assertEqual(r['partial'],1);self.assertEqual(r['statutory_missing'],6)
        todo=(self.root/'待下載清單.md').read_text(encoding='utf-8')
        self.assertIn('202601_6739_AI1.pdf',todo);self.assertIn('77-101',todo);self.assertIn('HTTP 403',json.dumps(data,ensure_ascii=False))
        gaps.refresh(self.s,self.c,'2026-10-02',years=1)
        self.assertEqual(len(read(self.root/'缺口清單.json')['gaps']),len(data['gaps']))  # auto entries replaced, not duplicated
        gaps.coverage_set(self.root,self.c,'2025 年報','1-101',101)
        self.assertEqual(len(read(self.root/'缺口清單.json')['partial']),1)

class ReadmeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'TPEX-6739'
        self.c=onboard(self.root,'TPEX','6739','竹陞科技','semiconductor')
    def tearDown(self):self.tmp.cleanup()
    def test_block_regenerates_and_keeps_researcher_text(self):
        text=(self.root/'README.md').read_text(encoding='utf-8')
        self.assertIn(readme.START,text);self.assertIn('Google Drive',text);self.assertIn('待產出',text)
        (self.root/'README.md').write_text(text.replace('## 接續原則','## 我的筆記\n保留這段\n\n## 接續原則'),encoding='utf-8')
        (self.root/'整合簡報/x.pptx').write_bytes(b'PK');(self.root/'工程圖解/01_a.svg').write_text('<svg><text>來源</text></svg>',encoding='utf-8')
        cli(self.root,'readme');new=(self.root/'README.md').read_text(encoding='utf-8')
        self.assertIn('保留這段',new);self.assertIn('x.pptx',new);self.assertIn('1 張仍為活字',new);self.assertEqual(new.count(readme.START),1)
        legacy=self.root/'README.md';legacy.write_text('# 舊README\n\n手寫內容\n',encoding='utf-8')
        readme.write(self.root,self.c);t=legacy.read_text(encoding='utf-8')
        self.assertTrue(t.startswith('# 舊README'));self.assertIn('手寫內容',t);self.assertIn(readme.END,t)
    def test_set_industry_equipment(self):
        r=cli(self.root,'set-industry','--industry','semiconductor-equipment')
        self.assertIn('驗收認列時點、在製品與合約負債',r['profile']['required_kpis'])
        self.assertEqual(read(self.root/'config.json')['industry'],'semiconductor-equipment')
        self.assertNotEqual(cli(self.root,'set-industry','--industry','nope',check=False).returncode,0)

if __name__=='__main__':unittest.main()
