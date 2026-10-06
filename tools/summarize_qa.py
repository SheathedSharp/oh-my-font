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
    outlines=load('outline-checks.json');conversion=load('conversion-checks.json')
    expected={r['file']:r['sha256'] for r in checks['records']}
    assert len(expected)==96
    assert outlines['source_passed'] and outlines['compiled_passed']
    assert len(outlines['source'])==32 and len(outlines['compiled'])==96
    assert {(r['family'],r['weight'],r['style']) for r in outlines['source']} == {(f,w,s) for f in ('LihuiT','zayJu') for w in (100,300,400,500,600,700,800,900) for s in ('upright','oblique')}
    for row in outlines['source']:
        source=ROOT/'sources/masters'/row['family']/f"{row['weight']}.json"
        assert hashlib.sha256(source.read_bytes()).hexdigest()==row['source_sha256']
        assert row['glyphs']==945 and row['codepoints']==810 and not row['invalid']
        assert all(check['passed'] for check in row['regressions'])
    assert {r['file']:r['sha256'] for r in outlines['compiled']}==expected
    assert all(r['native_curve_type_present'] and not r['findings'] and r['glyphs']==945 for r in outlines['compiled'])
    assert conversion['passed'] and len(conversion['records'])==32
    compared={}
    for row in conversion['records']:
        assert row['woff2_lossless'] and not row['findings'] and row['glyphs_compared']==945
        for fmt,digest in row['sha256'].items():
            compared[f"{fmt}/{row['family']}/{row['style']}.{fmt}"]=digest
    assert compared==expected
    manifest=json.loads((ROOT/'site/font-manifest.json').read_text())
    assert len(site['faces'])==32 and all(face['loaded'] for face in site['faces'])
    assert not site['page_errors'] and not site['failed_requests']
    assert manifest['version']==build['version'] and len(manifest['fonts'])==32
    assert {f['file'] for f in site['faces']}=={f['file'] for f in manifest['fonts']}
    for face in manifest['fonts']:
        digest=hashlib.sha256((ROOT/'site'/face['file']).read_bytes()).hexdigest()
        assert digest==face['sha256']==expected['woff2/'+face['file'].removeprefix('fonts/')]
    site['verified_font_sha256']={f['file']:f['sha256'] for f in manifest['fonts']}
    candidates=[{key:r[key] for key in ('file','sha256','family','style','codepoints','ots_exit','shaping_passed')} for r in checks['records']]
    optional={}
    for name in ('coretext-checks.json','installed-macos-checks.json'):
        path=ROOT/'.release-work'/name
        if path.exists():optional[name]=load(name)
    native=optional.get('coretext-checks.json')
    if native:
        assert len(native['records'])==64
        assert {r['file']:r['sha256'] for r in native['records']}=={n:d for n,d in expected.items() if n.startswith(('ttf/','otf/'))}
        assert all(r['no_fallback'] and r['process_registration'] for r in native['records'])
    installed=optional.get('installed-macos-checks.json')
    if installed:
        folder=Path.home()/f'Library/Fonts/oh-my-font-v{build["version"]}'
        for row in installed['records']:
            path=folder/row['file']
            expected=next(r['sha256'] for r in candidates if r['file'].endswith('/'+row['file']))
            assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
    report={'version':build['version'],'license':'OFL-1.1','source':'https://github.com/SheathedSharp/oh-my-font','author':'zayju','reserved_font_names':[],
            'scope':'Independent weight-master development candidate. All source and serialized glyph geometry, cross-format fidelity, OTS/metadata/shaping and web checks passed. Complete FontBakery universal profile retains the documented Sigma case-mapping FAIL and warnings. Not a release-publication, full-language/full-platform or manual approval of every glyph claim.',
            'build_inputs_sha256':build['source_inputs_sha256'],'tool_versions':checks['versions'],
            'files':len(candidates),'shaping_assertions':sum(r['shaping_passed'] for r in candidates),
            'full_ofl_and_original_source_metadata_verified':True,'candidates':candidates,
            'fontbakery':groups,'browser':site,'native':optional,
            'outlines':outlines,'conversion':conversion}
    for name in ('reproducibility','weight-isolation'):
        path=ROOT/'.release-work'/f'{name}.json'
        if path.exists():
            data=json.loads(path.read_text());assert data['passed']
            if name=='reproducibility':
                assert len(data['records'])==96
                assert {r['file']:r['sha256'] for r in data['records']}==expected
                assert all(r['identical'] and r['sha256']==r['rebuild_sha256'] for r in data['records'])
            report[name]=data
    proof=ROOT/f'docs/qa/{build["version"]}/proof-manifest.json'
    if proof.exists():
        data=json.loads(proof.read_text())
        for row in data['files']:
            name=row.get('file',row.get('comparison_file'))
            if name:
                assert name.startswith('dist/')
                assert row['sha256']==expected[name.removeprefix('dist/')]
        report['proof_manifest']=proof.relative_to(ROOT).as_posix()
        report['proof_manifest_sha256']=hashlib.sha256(proof.read_bytes()).hexdigest()
    out=ROOT/f'docs/qa/release-{build["version"]}.json';out.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(report,ensure_ascii=True,indent=2)+'\n'
    assert str(Path.home()) not in text
    out.write_text(text)
    print(f'Wrote {out.relative_to(ROOT)} for {len(candidates)} exact candidates.')

if __name__=='__main__':
    main()
