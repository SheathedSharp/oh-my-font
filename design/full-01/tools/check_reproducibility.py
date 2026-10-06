#!/usr/bin/env python3
"""Repeat the full six-file build into a fresh directory and compare exact bytes."""
import json,subprocess,sys,tempfile
from pathlib import Path
from build import ROOT,FULL,OUT,sha

def main():
    original=json.loads((OUT/'build.json').read_text())
    if original['stage']!='full-reference-review' or len(original['records'])!=6:raise ValueError('Full build missing')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='full-reference-rebuild-',dir=ROOT/'.release-work') as temp:
        target=Path(temp)
        subprocess.run([sys.executable,str(FULL/'tools/build.py'),'--output',str(target)],cwd=ROOT,check=True)
        rebuilt=json.loads((target/'build.json').read_text())
        if rebuilt['source_inputs']!=original['source_inputs']:raise ValueError('Input files changed during rebuild')
        for row in original['records']:
            current=sha(OUT/row['file']);new=sha(target/row['file'])
            if current!=row['sha256'] or new!=current:raise ValueError('Nondeterministic rebuild: '+row['file'])
            rows.append({'file':row['file'],'sha256':current,'rebuild_sha256':new,'identical':True})
    report={'scope':'Two independent output directories on the same machine and pinned toolchain; byte identity of all six reference fonts, not a cross-platform byte-identity assertion','records':rows,'passed':True}
    (OUT/'reproducibility.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS: 6/6 reference font files reproducible byte-for-byte.')
if __name__=='__main__':main()
