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
        if anchors.get('method')!='etf_implied_growth':errors.append('anchors.json default method must be etf_implied_growth (v3.7)')
        if anchors.get('model_version')!='v3.7b':errors.append('anchors.json model_version must be v3.7b')
        if '記憶體' not in anchors.get('excluded_themes',[]):errors.append('anchors.json excluded_themes must include 記憶體 (v3.7b)')
        if anchors.get('hurdle_rule')!='category_etf_growth_fy':errors.append('anchors.json hurdle_rule must be category_etf_growth_fy (v3.7b)')
        if 'hurdle' in anchors:errors.append('anchors.json must not define a single unified hurdle (v3.7b uses each category ETF G_FY)')
        for k,c in anchors['categories'].items():
            v=c.get('latest_known',{})
            if v.get('hurdle_growth')!=v.get('etf_growth_fy'):errors.append('anchors.json latest_known.hurdle_growth must equal etf_growth_fy: '+k)
        if not (isinstance(anchors.get('excess_cap'),(int,float)) and anchors['excess_cap']>0):errors.append('anchors.json excess_cap must be positive')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(anchors.get('latest_known',{}).get('asof',''))) or not anchors['latest_known'].get('source'):errors.append('anchors.json latest_known needs asof and source')
        legacy=anchors.get('legacy_dual_anchor',{}).get('ratios',{})
        for k,c in anchors['categories'].items():
            if 'ratio_p' in c or 'ratio_q' in c:errors.append('ratio_p/ratio_q only allowed under legacy_dual_anchor: '+k)
            v=c.get('latest_known',{})
            if not c.get('etf') or not all(isinstance(v.get(r),(int,float)) and v[r]>0 for r in ('etf_pe_trailing','etf_growth_ttm','etf_growth_fy','m_adj','base_pe')):errors.append('invalid anchor category: '+k)
            elif abs(v['etf_pe_trailing']/(1+v['etf_growth_ttm'])*v['m_adj']-v['base_pe'])>1e-3:errors.append('anchor base_pe inconsistent with ETF PE / (1+G_TTM) x M_adj: '+k)
            if not all(isinstance(legacy.get(k,{}).get(r),(int,float)) and 0<legacy[k][r]<=2 for r in ('ratio_p','ratio_q')):errors.append('invalid legacy anchor ratios: '+k)
        if not all(isinstance(anchors['rule'].get(r),(int,float)) for r in ('high_ratio','low_ratio','high_adj','low_adj')):errors.append('invalid anchor rule')
    except Exception as e:errors.append('profiles/anchors.json: '+str(e))
    return {'status':'passed' if not errors else 'failed','errors':errors,'skills':len(skills),'manifests':len(manifests),'scope':'offline structural and privacy checks only'}

if __name__=='__main__':
    result=validate(Path(__file__).resolve().parents[1]);print(json.dumps(result,indent=2));sys.exit(bool(result['errors']))
