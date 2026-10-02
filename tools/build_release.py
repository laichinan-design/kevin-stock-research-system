"""Kevin 股票研究 plugin 發行打包（從 repo 組出 dist/plugin-release-<版本>/，與 Drive「Kevin 股票分析Plugin」同結構）：結構檢查 → 單元測試 → Claude CLI 驗證 → 內層 .plugin → 解壓後重驗 → 雜湊 → 總 ZIP。"""
import hashlib, json, re, shutil, subprocess, sys, tempfile, zipfile
from datetime import date
from pathlib import Path
if Path(__file__).resolve().parent.name!='tools': raise SystemExit('run tools/build_release.py from the repo; the copy inside dist/ is for reference only')
REPO=Path(__file__).resolve().parents[1]; SRC=REPO/'plugins'/'kevin-stock-research'
VERSION=json.loads((SRC/'.claude-plugin'/'plugin.json').read_text(encoding='utf-8'))['version']
HERE=REPO/'dist'/f'plugin-release-{VERSION}'; BASE=HERE/'package'; PLUGIN=BASE/'plugins'/'kevin-stock-research'
if HERE.exists(): shutil.rmtree(HERE)
for src,dst in ((SRC,PLUGIN),(REPO/'release'/'.agents',BASE/'.agents')): shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
(BASE/'.claude-plugin').mkdir(parents=True); shutil.copy2(REPO/'.claude-plugin'/'marketplace.json',BASE/'.claude-plugin'/'marketplace.json')
for n in ('START-HERE.md','install-openai.ps1'): shutil.copy2(REPO/'release'/n,BASE/n)
shutil.copy2(Path(__file__),HERE/'build_release.py')
VERSION=json.loads((PLUGIN/'.claude-plugin'/'plugin.json').read_text(encoding='utf-8'))['version']
FINAL=HERE/f'Kevin股票研究Plugin_{VERSION}_ChatGPT_Claude.zip'
ANSI=re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
def sha(b): return hashlib.sha256(b).hexdigest()
def wj(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def run(a,cwd,check=True):
    r=subprocess.run(a,cwd=cwd,capture_output=True,timeout=900); log=ANSI.sub('',(r.stdout+r.stderr).decode('utf-8','replace'))
    if check and r.returncode: raise RuntimeError(f'{a} failed:\n{log}')
    return r.returncode,log
def clean(root):
    for d in list(root.rglob('__pycache__')): shutil.rmtree(d)
def files_of(root): return [p for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
def zip_tree(root,dest):
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files_of(root): z.write(p,p.relative_to(root).as_posix())
def check(plugin_root,package_root,claude):
    clean(plugin_root)
    st=json.loads(run([sys.executable,'-B','scripts/validate_package.py'],plugin_root)[1])
    if st['status']!='passed': raise RuntimeError(st)
    _,tests=run([sys.executable,'-B','-m','unittest','discover','-s','scripts','-p','test_*.py','-v'],plugin_root)
    count=int(re.search(r'Ran (\d+) tests',tests)[1]); skipped=len(re.findall(r'\.\.\. skipped',tests)); clean(plugin_root)
    out={'structural':st['status'],'tests':count,'skipped':skipped,'claude_cli':'not_run: claude CLI not found'}
    if claude:
        res={}
        for label,target in (('plugin',plugin_root),('marketplace',package_root)):
            code,log=run([claude,'plugin','validate',str(target)],HERE,check=False)
            res[label]={'exit_code':code,'passed':code==0 and 'Validation passed' in log}
            if not res[label]['passed']: raise RuntimeError(f'claude plugin validate {label}: {log}')
        out['claude_cli']=res
    return out,tests
manifests={n:json.loads((PLUGIN/n).read_text(encoding='utf-8')) for n in ('plugin.json','.claude-plugin/plugin.json','.codex-plugin/plugin.json')}
market=json.loads((BASE/'.claude-plugin'/'marketplace.json').read_text(encoding='utf-8'))
versions={n:m['version'] for n,m in manifests.items()}|{'claude marketplace':market['plugins'][0]['version'],'marketplace metadata':market['metadata']['version']}
versions['START-HERE']=re.search(r'(\d+\.\d+\.\d+)',(BASE/'START-HERE.md').read_text(encoding='utf-8').splitlines()[0])[1]
if set(versions.values())!={VERSION}: raise RuntimeError(f'version mismatch: {versions}')
codex=json.loads((BASE/'.agents'/'plugins'/'marketplace.json').read_text(encoding='utf-8'))
if (BASE/codex['plugins'][0]['source']['path']).resolve()!=PLUGIN.resolve(): raise RuntimeError('codex catalog path mismatch')
claude=shutil.which('claude'); cv=run([claude,'--version'],HERE)[1].strip() if claude else None
logs=BASE/'validation'; logs.mkdir(exist_ok=True)
src,tlog=check(PLUGIN,BASE,claude); (logs/'unit-tests.txt').write_text(tlog,encoding='utf-8')
with tempfile.TemporaryDirectory() as t:
    inner=Path(t)/'kevin-stock-research.plugin'; zip_tree(PLUGIN,inner)
    with zipfile.ZipFile(inner) as z:
        exp={p.relative_to(PLUGIN).as_posix():p.read_bytes() for p in files_of(PLUGIN)}
        if z.testzip() is not None or set(z.namelist())!=set(exp) or any(z.read(n)!=b for n,b in exp.items()): raise RuntimeError('.plugin differs from source')
    shutil.copy2(inner,BASE/inner.name)
val={'version':VERSION,'built_on':date.today().isoformat(),'python':sys.version.split()[0],'automated_tests_passed':src['tests'],'tests_skipped':src['skipped'],
     'tests_0_2_2_baseline':89,'new_cases_since_0_2_2':src['tests']-89,'structural_check':src['structural'],'claude_cli_version':cv,'claude_plugin_validate':src['claude_cli'],
     'official_skill_validator':'frontmatter rule enforced by scripts/validate_package.py',
     'openai_plugin_validator':'not_rerun: validator bundled with the Codex runtime; .codex-plugin manifest changed version only',
     'powershell_installer':{'changed_since_0_2_2':False,'actual_install':'not_run'},
     'render_checks':'unit tests render SVG/PPTX structurally; visual checks are recorded per research run',
     'extracted_release_check':'pending','claude_archive_matches_source':True,'live_market_adapter_validation':'not_run',
     'chatgpt_account_installation':'not_run','claude_account_installation':'not_run','existing_schedules_changed':False,
     'limits':['TPEX/US live adapters unsupported; verified imported snapshots supported','Drive upload of binaries is manual; plugin does not connect to Drive',
               'engineering-visuals/integrated-deck need fonttools/cairosvg/python-pptx and a Traditional Chinese font','Kevin results are scenario calculations requiring researcher evidence']}
wj(BASE/'RELEASE-VALIDATION.json',val)
with tempfile.TemporaryDirectory() as t:
    cand=Path(t)/'c.zip'; zip_tree(BASE,cand); ex=Path(t)/'x'
    with zipfile.ZipFile(cand) as z:
        for n in z.namelist():
            if Path(n).is_absolute() or '..' in Path(n).parts: raise RuntimeError('unsafe entry '+n)
        z.extractall(ex)
    exc,elog=check(ex/'plugins'/'kevin-stock-research',ex,claude); (logs/'extracted-tests.txt').write_text(elog,encoding='utf-8')
    if exc['tests']!=src['tests']: raise RuntimeError('extracted test count differs')
val['extracted_release_check']={'status':'passed',**exc}; wj(BASE/'RELEASE-VALIDATION.json',val)
clean(BASE)
hashes={p.relative_to(BASE).as_posix():sha(p.read_bytes()) for p in files_of(BASE) if p.name!='FILE-HASHES.json'}
wj(BASE/'FILE-HASHES.json',{'algorithm':'SHA256','excludes':['FILE-HASHES.json'],'files':hashes})
if FINAL.exists(): FINAL.unlink()
zip_tree(BASE,FINAL)
with zipfile.ZipFile(FINAL) as z:
    if z.testzip() is not None or any(sha(z.read(n))!=h for n,h in hashes.items()): raise RuntimeError('final zip verification failed')
    entries=len(z.namelist())
summary={'file':FINAL.name,'bytes':FINAL.stat().st_size,'sha256':sha(FINAL.read_bytes()),'archive_entries':entries,'tests_passed':src['tests'],
         'unpacked_tests_passed':exc['tests'],'claude_plugin_validate':'passed (plugin + marketplace, source and extracted)' if claude else 'not_run'}
wj(HERE/'release-summary.json',summary); print(json.dumps(summary,ensure_ascii=False,indent=2))
