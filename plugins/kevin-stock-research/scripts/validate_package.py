"""Offline package integrity checks independent of the hosting platform."""
import ast,json,re,sys
from pathlib import Path

VERSION='0.8.1'

def validate(root):
    root=Path(root);errors=[];manifests=[]
    for name in ('plugin.json','.codex-plugin/plugin.json','.claude-plugin/plugin.json'):
        p=root/name
        try:
            item=json.loads(p.read_text(encoding='utf-8'));manifests.append(item)
            if item.get('name')!='kevin-stock-research' or item.get('version')!=VERSION:errors.append('manifest identity/version mismatch: '+name)
        except Exception as e:errors.append(name+': '+str(e))
    for p in root.rglob('*'):
        if not p.is_file():continue
        relative=p.relative_to(root).as_posix()
        if any(x in p.parts for x in ('__pycache__','.venv','node_modules')) or p.suffix in ('.pyc','.sqlite','.xlsx','.pdf'):errors.append('runtime/private artifact in package: '+relative)
        if p.suffix in ('.json','.md','.py','.txt'):
            text=p.read_text(encoding='utf-8')
            if re.search(r'[A-Za-z]:[\\/]'+'Users[\\/]',text):errors.append('absolute user path: '+relative)
            if p.suffix=='.json':
                try:json.loads(text)
                except Exception as e:errors.append(relative+': '+str(e))
            if p.suffix=='.py':
                try:ast.parse(text)
                except SyntaxError as e:errors.append(relative+': '+str(e))
    skills=list((root/'skills').glob('*/SKILL.md'))
    if len(skills)!=10:errors.append('expected 10 skills')
    for p in skills:
        text=p.read_text(encoding='utf-8');m=re.match(r'^---\nname: ([a-z0-9-]+)\ndescription: ([^\n]+)\n---\n',text)
        if not m or m[1]!=p.parent.name:errors.append('invalid minimal skill frontmatter: '+p.parent.name)
        for relative in re.findall(r'\.\./\.\./[A-Za-z0-9_./-]+',text):
            if not (p.parent/relative.rstrip('.')).exists():errors.append('missing skill reference: '+relative)
    industries=list((root/'profiles/industries').glob('*.json'))
    if len(industries)!=10:errors.append('expected 10 industries')
    methods={'kevin_legacy','scenario_pe','scenario_pb','nav'}
    for p in industries:
        try:
            d=json.loads(p.read_text(encoding='utf-8'))
            if d.get('id')!=p.stem or not d.get('name') or not d.get('required_kpis') or not isinstance(d.get('guards'),list) or not d.get('peer_rules'):errors.append('invalid industry profile: '+p.stem)
            if not set(d.get('candidate_methods',[]))<=methods:errors.append('unknown valuation method in profile: '+p.stem)
            for k in ('visual_templates','deck_focus'):
                if k in d and not (isinstance(d[k],list) and d[k] and all(isinstance(x,str) and x for x in d[k])):errors.append(f'invalid {k}: '+p.stem)
        except Exception as e:errors.append(p.name+': '+str(e))
    try:
        anchors=json.loads((root/'profiles/anchors.json').read_text(encoding='utf-8'))
        if set(anchors['categories'])!={'portfolio','cpo','potential'}:errors.append('anchors.json categories changed')
        for k,c in anchors['categories'].items():
            if not c.get('etf') or any(r in c for r in ('ratio_p','ratio_q')):errors.append('invalid anchor category (v3.7b has no dual-anchor ratios): '+k)
        for k in ('excess_cap','low_base_growth','shortfall_floor','peak_pe','stale_days'):
            if not isinstance(anchors.get(k),(int,float)) or anchors[k]<=0:errors.append('invalid anchors.json '+k)
        if anchors.get('excluded_theme')!='記憶體' or not anchors.get('memory_codes'):errors.append('anchors.json must list the excluded memory-theme codes')
        known=anchors.get('last_known',{})
        if set(known.get('categories',{}))!={'portfolio','cpo','potential'} or not known.get('asof') or not known.get('source'):errors.append('anchors.json last_known incomplete')
        if not all(isinstance(anchors['rule'].get(r),(int,float)) for r in ('high_ratio','low_ratio','high_adj','low_adj')):errors.append('invalid anchor rule')
    except Exception as e:errors.append('profiles/anchors.json: '+str(e))
    return {'status':'passed' if not errors else 'failed','errors':errors,'skills':len(skills),'manifests':len(manifests),'scope':'offline structural and privacy checks only'}

if __name__=='__main__':
    result=validate(Path(__file__).resolve().parents[1]);print(json.dumps(result,indent=2));sys.exit(bool(result['errors']))
