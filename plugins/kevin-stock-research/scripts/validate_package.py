"""Offline package integrity checks independent of the hosting platform."""
import ast,json,re,sys
from pathlib import Path

VERSION='0.3.0'

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
    if len(skills)!=8:errors.append('expected 8 skills')
    for p in skills:
        text=p.read_text(encoding='utf-8');m=re.match(r'^---\nname: ([a-z0-9-]+)\ndescription: ([^\n]+)\n---\n',text)
        if not m or m[1]!=p.parent.name:errors.append('invalid minimal skill frontmatter: '+p.parent.name)
        for relative in re.findall(r'\.\./\.\./[A-Za-z0-9_./-]+',text):
            if not (p.parent/relative.rstrip('.')).exists():errors.append('missing skill reference: '+relative)
    if len(list((root/'profiles/industries').glob('*.json')))!=7:errors.append('expected 7 industries')
    try:
        anchors=json.loads((root/'profiles/anchors.json').read_text(encoding='utf-8'))
        if set(anchors['categories'])!={'portfolio','cpo','potential'}:errors.append('anchors.json categories changed')
        for k,c in anchors['categories'].items():
            if not all(isinstance(c.get(r),(int,float)) and 0<c[r]<=2 for r in ('ratio_p','ratio_q')) or not c.get('etf'):errors.append('invalid anchor category: '+k)
        if not all(isinstance(anchors['rule'].get(r),(int,float)) for r in ('high_ratio','low_ratio','high_adj','low_adj')):errors.append('invalid anchor rule')
    except Exception as e:errors.append('profiles/anchors.json: '+str(e))
    return {'status':'passed' if not errors else 'failed','errors':errors,'skills':len(skills),'manifests':len(manifests),'scope':'offline structural and privacy checks only'}

if __name__=='__main__':
    result=validate(Path(__file__).resolve().parents[1]);print(json.dumps(result,indent=2));sys.exit(bool(result['errors']))
