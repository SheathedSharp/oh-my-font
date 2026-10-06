#!/usr/bin/env python3
"""Bind official release QA to exactly the current approved sources and font files."""
import io,json,unittest
from pathlib import Path
from release_support import ROOT,WORK,DIST,read_build,version,sha

def main():
    build=read_build();expected={r['file']:r['sha256'] for r in build['records']}
    read=lambda name:json.loads((WORK/name).read_text())
    checks=read('candidate-checks.json');fb=read('fontbakery-summary.json');site=read('site-checks.json');repro=read('reproducibility.json')
    assert checks['passed'] and checks['source_inputs_sha256']==build['source_inputs_sha256']
    assert {r['file']:r['sha256'] for r in checks['records']}==expected
    assert {r['file']:r['sha256'] for r in checks['forced_decomposition']}==expected
    assert all(r['approved_glyphs_and_layout_identical'] and r['ots_exit']==0 and r['serialized_glyphs_checked']==986 for r in checks['records'])
    assert all(r['pairs_checked']==2964 and not r['failures'] for r in checks['forced_decomposition'])
    assert fb['passed'] and len(fb['groups'])==4
    assert {r['file']:r['sha256'] for r in fb['groups']}=={n:v for n,v in expected.items() if n.endswith(('.ttf','.otf'))}
    assert all(not r['unexpected'] and len(r['accepted_failures'])==1 for r in fb['groups'])
    assert len(site['faces'])==2 and all(r['loaded'] and r['weight']==400 and r['style']=='normal' for r in site['faces'])
    assert site['font_sha256']=={Path(n).name:v for n,v in expected.items() if n.endswith('.woff2')}
    assert not site['page_errors'] and not site['failed_requests']
    manifest=json.loads((ROOT/'site/font-manifest.json').read_text());assert manifest['version']==version() and len(manifest['fonts'])==2
    for face in manifest['fonts']:
        assert sha(ROOT/'site'/face['file'])==face['sha256']==expected['woff2/'+face['file'].removeprefix('fonts/')]
    assert repro['passed'] and {r['file']:r['sha256'] for r in repro['records']}==expected
    assert all(r['identical'] and r['sha256']==r['rebuild_sha256'] for r in repro['records'])
    native=None
    if (WORK/'coretext-checks.json').exists():
        native=read('coretext-checks.json');assert native['passed']
        assert {r['file']:r['sha256'] for r in native['records']}=={n:v for n,v in expected.items() if n.endswith(('.ttf','.otf'))}
        assert all(r['exact_file'] and r['no_fallback'] for r in native['records'])
    log=io.StringIO();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'));result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    if not result.wasSuccessful():print(log.getvalue());raise SystemExit('Release unit tests failed')
    (WORK/'unit-tests.log').write_text(log.getvalue())
    report={'version':version(),'scope':'Owner-approved complete redesign; two Regular 400 upright faces only. Exact outputs preserve approved drawings/metrics/layout. Other weights, obliques, full Unicode and full-platform coverage are not claimed.',
            'approval_commit':build['approved_commit'],'license':'OFL-1.1','author':'zayju','source':'https://github.com/SheathedSharp/oh-my-font',
            'build_inputs_sha256':build['source_inputs_sha256'],'files':6,'faces':2,'build':build,'candidates':checks,'fontbakery':fb,'browser':site,'native_macos':native,'reproducibility':repro,'unit_tests':{'count':result.testsRun,'passed':True}}
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    assert '/Users/' not in text and '/home/' not in text
    dest=ROOT/'docs/qa'/f'release-{version()}.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
    print('Wrote',dest.relative_to(ROOT),'for the exact 6 official candidates.')
if __name__=='__main__':main()
