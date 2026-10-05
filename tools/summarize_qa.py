#!/usr/bin/env python3
"""Create a path-sanitized QA record bound to current source and font hashes."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main() -> None:
    def load(name: str):
        return json.loads((ROOT/'.release-work'/name).read_text())
    build=json.loads((ROOT/'dist/build-report.json').read_text())
    checks=load('candidate-checks.json'); groups=load('fontbakery-summary.json'); site=load('site-checks.json')
    assert len(checks['records'])==96 and all(r['ots_exit']==0 and r.get('shaping_passed')==15 for r in checks['records'])
    assert len(groups)==4 and all(r['scoped_release_gate']=='passed' for r in groups)
    for name,expected in build['source_inputs_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected, name
    for record in checks['records']:
        assert hashlib.sha256((ROOT/'dist'/record['file']).read_bytes()).hexdigest()==record['sha256']
    candidates=[{key:r[key] for key in ('file','sha256','family','style','codepoints','ots_exit','shaping_passed')} for r in checks['records']]
    optional={}
    for name in ('coretext-checks.json','installed-macos-checks.json'):
        path=ROOT/'.release-work'/name
        if path.exists():optional[name]=load(name)
    installed=optional.get('installed-macos-checks.json')
    if installed:
        folder=Path.home()/f'Library/Fonts/oh-my-font-v{build["version"]}'
        for row in installed['records']:
            path=folder/row['file']
            expected=next(r['sha256'] for r in candidates if r['file'].endswith('/'+row['file']))
            assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
    report={'version':build['version'],'license':'OFL-1.1','source':'https://github.com/SheathedSharp/oh-my-font','author':'zayju','reserved_font_names':[],
            'scope':'First public Latin text/display release. OTS/metadata/shaping/web checks passed; complete FontBakery universal profile retains the precisely documented Sigma case-mapping FAIL and warnings. Not a full-language/full-platform or manual author sign-off claim.',
            'build_inputs_sha256':build['source_inputs_sha256'],'tool_versions':checks['versions'],
            'files':len(candidates),'shaping_assertions':sum(r['shaping_passed'] for r in candidates),
            'full_ofl_and_original_source_metadata_verified':True,'candidates':candidates,
            'fontbakery':groups,'browser':site,'native':optional}
    out=ROOT/f'docs/qa/release-{build["version"]}.json';out.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(report,ensure_ascii=True,indent=2)+'\n'
    assert str(Path.home()) not in text
    out.write_text(text)
    print(f'Wrote {out.relative_to(ROOT)} for {len(candidates)} exact candidates.')

if __name__=='__main__':
    main()
