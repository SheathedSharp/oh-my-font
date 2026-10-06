"""Single release contract for approved source, exact filenames and candidate hashes."""
from __future__ import annotations
import hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FULL=ROOT/'design/full-01'
DIST=ROOT/'dist'
WORK=ROOT/'.release-work'
FAMILIES=('LihuiT','zayJu')
FORMATS=('ttf','otf','woff2')

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def version()->str:
    value=(ROOT/'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d{3}',value):raise ValueError('Expected OpenType version such as 0.400')
    return value

def expected_files()->set[str]:
    return {f'{fmt}/{family}/{family}-Regular.{fmt}' for family in FAMILIES for fmt in FORMATS}

def validate_approval()->dict:
    spec=json.loads((ROOT/'config/approved-reference.json').read_text())
    if spec['families']!=list(FAMILIES) or spec['weight']!=400 or spec['glyphs']!=986 or spec['codepoints']!=810:
        raise ValueError('Unapproved release inventory')
    for name,digest in spec['approved_inputs'].items():
        path=ROOT/name
        if not path.is_file() or path.is_symlink() or sha(path)!=digest:raise ValueError('Approved reference input changed: '+name)
    return spec

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod

reference=module('approved_reference_build',FULL/'tools/build.py')

def reference_checks():
    # The historic check's helpers refer to its own build module. Bind that only
    # while loading the helpers; never execute the draft-output main routine.
    before=sys.modules.get('build');sys.modules['build']=reference
    try:return module('approved_reference_checks',FULL/'tools/check.py')
    finally:
        if before is None:sys.modules.pop('build',None)
        else:sys.modules['build']=before

def source_hashes()->dict:
    files={ROOT/'VERSION',ROOT/'OFL.txt',ROOT/'ATTRIBUTION.txt',ROOT/'AUTHORS.txt',ROOT/'FONTLOG.txt',ROOT/'LICENSE.md',ROOT/'build.py',ROOT/'requirements.txt',ROOT/'requirements-qa.txt',ROOT/'config/approved-reference.json'}
    spec=validate_approval();files.update(ROOT/name for name in spec['approved_inputs'])
    files.update((ROOT/'tools').glob('*.py'));files.update((ROOT/'tools').glob('*.swift'));files.update((ROOT/'tests').glob('*.py'))
    for name in ('index.html','app.js','style.css','favicon.ico'):files.add(ROOT/'site'/name)
    files.update(p for p in (ROOT/'site/assets').rglob('*') if p.is_file())
    files.update((ROOT/'.github/workflows').glob('*.yml'))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files) if p.is_file()}

def read_build(dist=DIST)->dict:
    report=json.loads((dist/'build-report.json').read_text())
    if report['version']!=version() or report['scope']!='approved-regular-only' or report['files']!=6:
        raise ValueError('Missing current six-file approved release build')
    if {r['file'] for r in report['records']}!=expected_files():raise ValueError('Unexpected candidate inventory')
    actual={p.relative_to(dist).as_posix() for fmt in FORMATS for p in (dist/fmt).glob('*/*') if p.is_file()}
    if actual!=expected_files():raise ValueError('Stale or unexpected fonts in dist')
    for row in report['records']:
        if sha(dist/row['file'])!=row['sha256']:raise ValueError('Candidate hash changed: '+row['file'])
    if report['source_inputs_sha256']!=source_hashes():raise ValueError('Release inputs changed; rebuild and repeat checks')
    return report
