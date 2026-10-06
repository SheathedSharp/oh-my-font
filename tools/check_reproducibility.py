#!/usr/bin/env python3
"""Rebuild into an independent directory; verify all six official font bytes."""
import json,subprocess,sys,tempfile
from pathlib import Path
from release_support import ROOT,WORK,DIST,read_build,sha

def main():
    before=read_build();rows=[]
    with tempfile.TemporaryDirectory(prefix='release-rebuild-',dir=WORK) as folder:
        target=Path(folder);subprocess.run([sys.executable,str(ROOT/'build.py'),'--output',str(target)],cwd=ROOT,check=True)
        other=read_build(target);assert other['source_inputs_sha256']==before['source_inputs_sha256']
        for r in before['records']:
            a=sha(DIST/r['file']);b=sha(target/r['file']);assert a==b==r['sha256'],r['file']
            rows.append({'file':r['file'],'sha256':a,'rebuild_sha256':b,'identical':True})
    (WORK/'reproducibility.json').write_text(json.dumps({'scope':'Two full builds in independent directories on the same machine; not a cross-platform byte-identity promise','records':rows,'passed':True},indent=2)+'\n')
    print('PASS: 6 official files byte-identical after independent rebuild.')
if __name__=='__main__':main()
