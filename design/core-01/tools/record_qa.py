#!/usr/bin/env python3
"""Bind the limited-scope results and visual proof metadata to exact input files."""
import hashlib,json
from pathlib import Path
from build import ROOT,STUDY

def main():
    out=ROOT/'.release-work/core-01';build=json.loads((out/'build.json').read_text())
    checks=json.loads((out/'checks.json').read_text());browser=json.loads((out/'browser.json').read_text())
    proofs=json.loads((STUDY/'proofs/manifest.json').read_text())
    assert checks['passed'] and browser['passed']
    assert checks['sources']==build['sources']==proofs['sources']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for file,expected in build['sources'].items():assert sha(ROOT/file)==expected,file
    expected={row['file']:row['sha256'] for row in build['records']}
    assert {row['file']:row['sha256'] for row in checks['files']}==expected
    for file,value in expected.items():assert sha(out/file)==value,file
    assert browser['font_sha256']=={Path(n).name:v for n,v in expected.items() if n.endswith('.woff2')}
    for row in proofs['font_inputs']:
        if 'file' in row:assert expected[row['file']]==row['sha256']
    for file,value in proofs['proof_files'].items():assert sha(STUDY/'proofs'/file)==value,file
    native=None
    if (out/'coretext.json').exists():
        native=json.loads((out/'coretext.json').read_text());assert native['passed']
        assert {r['file']:r['sha256'] for r in native['files']}=={n:d for n,d in expected.items() if n.endswith(('.ttf','.otf'))}
    summary={'stage':'core-01-visual-review','visual_approval':'pending for all 22 proposed glyphs','scope':'11 proposed glyphs per family, one reference cut, plus technical .notdef and space only',
             'not_done':['remaining characters','additional weights','obliques/italics','font installation','production replacement','merge','release','deployment'],
             'build':build,'technical':checks,'browser':browser,'native_macos':native,
             'proof_manifest_sha256':sha(STUDY/'proofs/manifest.json')}
    target=STUDY/'qa.json';text=json.dumps(summary,ensure_ascii=False,indent=2)+'\n'
    assert '/Users/' not in text and '/home/' not in text
    target.write_text(text);print('Recorded exact core-study results. Visual approval still pending.')
if __name__=='__main__':main()
