#!/usr/bin/env python3
"""Produce a path-sanitized verification record bound to current source and files."""
import json,unittest,sys,io,hashlib
from pathlib import Path
from build import ROOT,FULL,OUT,FAMILIES,load,sha

def main():
    read=lambda name:json.loads((OUT/name).read_text())
    build=read('build.json');checks=read('checks.json');fb=read('fontbakery-summary.json')
    browser=read('browser.json');companion=read('glyphs-roundtrip.json');repro=read('reproducibility.json')
    assert build['stage']=='full-reference-review' and len(build['records'])==6
    expected={r['file']:r['sha256'] for r in build['records']};assert len(expected)==6
    for name,value in build['source_inputs'].items():assert sha(ROOT/name)==value,('stale input',name)
    for name,value in expected.items():assert sha(OUT/name)==value,('changed font',name)
    assert checks['passed'] and checks['source_inputs']==build['source_inputs']
    assert {r['file']:r['sha256'] for r in checks['files']}==expected
    assert {r['file']:r['sha256'] for r in checks['forced_decomposition']}==expected
    assert all(r['approved_core_unchanged'] and r['all_source_valid'] and r['codepoints']==810 and r['glyphs']==986 for r in checks['source'])
    assert all(not r['failures'] and r['pairs_checked']==2964 and len(r['feature_comparisons'])==6 for r in checks['forced_decomposition'])
    assert all(not r['findings'] and r['woff2_lossless'] and len(r['records'])==986 for r in checks['conversion'])
    assert fb['passed'] and len(fb['groups'])==4
    assert {r['file']:r['sha256'] for r in fb['groups']}=={n:v for n,v in expected.items() if n.endswith(('.ttf','.otf'))}
    assert all(not r['unexpected'] and len(r['accepted_failures'])==1 for r in fb['groups'])
    assert browser['passed'] and not browser['page_errors'] and not browser['failed_requests']
    assert browser['font_sha256']=={Path(n).name:v for n,v in expected.items() if n.endswith('.woff2')}
    assert companion['passed'] and len(companion['records'])==2
    for r in companion['records']:
        assert r['glyphs_checked']==986 and r['companion_sha256']==sha(FULL/'sources'/f"{r['family']}-Reference.glyphs")
    assert repro['passed'] and {r['file']:r['sha256'] for r in repro['records']}==expected
    assert all(r['sha256']==r['rebuild_sha256'] and r['identical'] for r in repro['records'])
    manifest=json.loads((FULL/'proofs/manifest.json').read_text())
    assert manifest['source_inputs']==build['source_inputs']
    assert {r['file']:r['sha256'] for r in manifest['font_inputs']}=={n:v for n,v in expected.items() if n.endswith('.otf')}
    for p,value in manifest['proofs'].items():assert sha(FULL/'proofs'/p)==value,('stale proof',p)
    for family in FAMILIES:
        names=[name for page in manifest['atlas'] if page['family']==family for name in page['glyphs']]
        assert len(names)==len(set(names))==986 and set(names)==set(load(family).keys())
    native=None
    if (OUT/'coretext.json').exists():
        native=read('coretext.json');assert native['passed']
        assert {r['file']:r['sha256'] for r in native['records']}=={n:v for n,v in expected.items() if n.endswith(('.ttf','.otf'))}
        assert all(r['no_fallback'] and r['exact_file'] and r['sample_lines']==12 and r['encoded_characters_mapped']==790 for r in native['records'])
    buffer=io.StringIO();suite=unittest.defaultTestLoader.discover(str(FULL/'tests'))
    result=unittest.TextTestRunner(stream=buffer,verbosity=2).run(suite)
    if not result.wasSuccessful():print(buffer.getvalue());raise SystemExit('Unit tests failed')
    (OUT/'unit-tests.log').write_text(buffer.getvalue())
    report={'stage':'full-reference-review','approved':'22 Core01 curves and advances; remaining repertoire expansion was requested by owner','pending':'Final optical acceptance of newly completed characters','scope':'One reference cut per family. 810 codepoints and 986 glyphs each; original 945 glyph names plus 41 explicit unencoded layout companions. No additional weights, Unicode scripts, installation, merge, release or deployment.',
       'build':build,'technical':checks,'fontbakery':fb,'browser':browser,'native_macos':native,'glyphs_roundtrip':companion,'reproducibility':repro,
       'regression_tests':{'count':result.testsRun,'passed':True},'proof_manifest_sha256':sha(FULL/'proofs/manifest.json'),
       'counts':{'source_glyphs':1972,'serialized_glyphs':sum(r['serialized_glyphs_checked'] for r in checks['files']),
                 'encoded_shape_checks':sum(r['encoded_character_checks'] for r in checks['files']),
                 'layout_regressions':sum(len(r['layout_regressions']) for r in checks['files']),
                 'ordinary_canonical_pairs':sum(r['canonical_equivalence_checks'] for r in checks['files']),
                 'forced_feature_canonical_pairs':sum(r['pairs_checked'] for r in checks['forced_decomposition']),
                 'retained_fontbakery_fails':sum(len(r['accepted_failures']) for r in fb['groups']),
                 'retained_fontbakery_warn_checks':sum(len(r['warnings']) for r in fb['groups'])}}
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if '/Users/' in text or '/home/' in text:raise ValueError('Private filesystem path in public QA report')
    (FULL/'qa.json').write_text(text);print('Wrote complete reference QA with current hashes;',result.testsRun,'regressions passed. New glyph optical approval remains pending.')
if __name__=='__main__':main()
