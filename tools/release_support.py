"""Single release contract for the 0.500 multi-weight family.

Regular 400 upright still compiles from the hash-locked 0.400 drawings.
Every other style is a stored UFO master under design/weights-0500.
Nothing in this module synthesizes a weight at build time.
"""
from __future__ import annotations
import hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FULL=ROOT/'design/full-01'
DIST=ROOT/'dist'
WORK=ROOT/'.release-work'
FAMILIES=('LihuiT','zayJu')
FORMATS=('ttf','otf','woff2')
WEIGHTS=(100,300,400,500,600,700,800,900)
WEIGHT_NAMES={100:'Thin',300:'Light',400:'Regular',500:'Medium',600:'Semibold',700:'Bold',800:'Extrabold',900:'Black'}
PANOSE_WEIGHT={100:2,300:3,400:5,500:6,600:7,700:8,800:9,900:10}
FILE_COUNT=len(FAMILIES)*len(WEIGHTS)*2*len(FORMATS)

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def version()->str:
    value=(ROOT/'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d{3}',value):raise ValueError('Expected OpenType version such as 0.500')
    return value

def style_name(weight,oblique):
    name=WEIGHT_NAMES[weight]
    if not oblique:return name
    return 'Oblique' if weight==400 else f'{name} Oblique'

def ps_name(family,weight,oblique):
    return family+'-'+style_name(weight,oblique).replace(' ','')

def styles():
    """Upright then Oblique within each weight, lightest first."""
    return [{'weight':weight,'oblique':oblique,'style':style_name(weight,oblique)} for weight in WEIGHTS for oblique in (False,True)]

def legacy_names(family,weight,oblique):
    """Windows name IDs 1 and 2, then typographic IDs 16 and 17.

    Name ID 2 stays inside the Regular/Bold/Italic/Bold Italic set so style
    linking works. Oblique is the typographic subfamily and the file name.
    That Italic token is not a claim of a separately drawn italic.
    """
    typographic=style_name(weight,oblique)
    if weight==400 and not oblique:return family,'Regular',family,'Regular'
    if weight==700 and not oblique:return family,'Bold',family,'Bold'
    if weight==400 and oblique:return family,'Italic',family,'Oblique'
    if weight==700 and oblique:return family,'Bold Italic',family,'Bold Oblique'
    return f'{family} {WEIGHT_NAMES[weight]}',('Italic' if oblique else 'Regular'),family,typographic

def font_path(fmt,family,weight,oblique):
    return f'{fmt}/{family}/{ps_name(family,weight,oblique)}.{fmt}'

def expected_files()->set[str]:
    return {font_path(fmt,family,row['weight'],row['oblique']) for family in FAMILIES for row in styles() for fmt in FORMATS}

def master_path(family,weight,oblique):
    if weight==400 and not oblique:return None
    return ROOT/'design/weights-0500/sources'/family/(ps_name(family,weight,oblique).split('-',1)[1]+'.ufo')

def full_decomposition_targets():
    """Upright masters plus the lightest and heaviest Oblique, desktop TTF.

    The other Obliques are 10° derivatives of masters that take this gate.
    They still get shaping checks and a fixed review-glyph sample.
    """
    rows=[]
    for family in FAMILIES:
        for row in styles():
            if row['oblique'] and row['weight'] not in (400,900):continue
            rows.append((family,row['weight'],row['oblique'],font_path('ttf',family,row['weight'],row['oblique'])))
    return rows

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
    weight=ROOT/'design/weights-0500'
    files.add(weight/'spec.py');files.update((weight/'tools').glob('*.py'))
    files.update(p for p in (weight/'sources').rglob('*') if p.is_file() and '_work.ufo' not in p.parts and '__pycache__' not in p.parts)
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files) if p.is_file()}

def read_build(dist=DIST)->dict:
    report=json.loads((dist/'build-report.json').read_text())
    if report['version']!=version() or report['scope']!='multiweight-0500' or report['files']!=FILE_COUNT:
        raise ValueError('Missing current 96-file multi-weight release build')
    if {r['file'] for r in report['records']}!=expected_files():raise ValueError('Unexpected candidate inventory')
    actual={p.relative_to(dist).as_posix() for fmt in FORMATS for p in (dist/fmt).glob('*/*') if p.is_file()}
    if actual!=expected_files():raise ValueError('Stale or unexpected fonts in dist')
    for row in report['records']:
        if sha(dist/row['file'])!=row['sha256']:raise ValueError('Candidate hash changed: '+row['file'])
    if report['source_inputs_sha256']!=source_hashes():raise ValueError('Release inputs changed; rebuild and repeat checks')
    return report
