"""Read-only local runtime and package preflight; no network or account changes."""
import importlib.util,json,sys
from pathlib import Path
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parents[1]
result={'version':json.loads((root/'plugin.json').read_text(encoding='utf-8'))['version'],
        'python_supported':sys.version_info>=(3,11),
        'dependencies':{name:importlib.util.find_spec(name) is not None for name in ('openpyxl','pypdfium2')},
        'skill_count':len(list((root/'skills').glob('*/SKILL.md'))),
        'live_data_validation':'not_run','host_installation_validation':'not_run',
        'schedule_enabled_by_install':False}
print(json.dumps(result,ensure_ascii=False,indent=2))
sys.exit(0 if result['python_supported'] and all(result['dependencies'].values()) else 1)
