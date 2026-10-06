#!/usr/bin/env python3
"""Verify local or freshly downloaded release archives without extracting/installing fonts."""
import argparse,hashlib,io,json,re,stat,zipfile
from pathlib import Path,PurePosixPath
from fontTools.ttLib import TTFont
from release_support import expected_files

def digest(data):return hashlib.sha256(data).hexdigest()
def sums(data):
    rows={}
    for line in data.decode().splitlines():
        hash_,name=line.split('  ',1)
        if not re.fullmatch(r'[0-9a-f]{64}',hash_) or name in rows:raise ValueError('Invalid or duplicate checksum entry')
        p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe checksum path')
        rows[name]=hash_
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True,type=Path);p.add_argument('--version',required=True);p.add_argument('--commit',required=True)
    a=p.parse_args();folder=a.directory;outer=sums((folder/'SHA256SUMS.txt').read_bytes())
    names={f'LihuiT-zayJu-v{a.version}-{s}.zip' for s in ('TTF','OTF','WOFF2','Website')}|{'BUILD-MANIFEST.json','QA.json'}
    assert set(outer)==names and {x.name for x in folder.iterdir() if x.is_file()}==names|{'SHA256SUMS.txt'}
    for name,value in outer.items():assert digest((folder/name).read_bytes())==value,name
    manifest=json.loads((folder/'BUILD-MANIFEST.json').read_text());qa=json.loads((folder/'QA.json').read_text())
    assert manifest['version']==a.version and manifest['commit']==a.commit and manifest['tag']=='v'+a.version
    assert manifest['faces']==2 and manifest['styles']==['Regular'] and manifest['weight']==400
    expected={r['file']:r['sha256'] for r in manifest['fonts']};assert set(expected)==expected_files()
    assert qa['version']==a.version and {r['file']:r['sha256'] for r in qa['candidates']['records']}==expected
    counts={};fonts_checked=0
    for kind in ('TTF','OTF','WOFF2','Website'):
        prefix=f'LihuiT-zayJu-v{a.version}-{kind}';path=folder/(prefix+'.zip')
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None;entries={}
            for info in z.infolist():
                assert info.filename.startswith(prefix+'/') and not stat.S_ISLNK(info.external_attr>>16)
                name=info.filename[len(prefix)+1:];p=PurePosixPath(name)
                assert name and not p.is_absolute() and '..' not in p.parts and name not in entries
                entries[name]=z.read(info)
            checks=sums(entries['SHA256SUMS.txt']);assert set(checks)==set(entries)-{'SHA256SUMS.txt'}
            for name,value in checks.items():assert digest(entries[name])==value,name
            assert all(n in entries for n in ('OFL.txt','ATTRIBUTION.txt','AUTHORS.txt','FONTLOG.txt','LICENSE.md','SOURCE.json','README.txt'))
            source=json.loads(entries['SOURCE.json']);assert source['version']==a.version and source['commit']==a.commit and source['faces']==2
            font_files={n:data for n,data in entries.items() if n.endswith(('.ttf','.otf','.woff2'))};assert len(font_files)==2
            for name,data in font_files.items():
                fmt=name.rsplit('.',1)[-1];relative=fmt+'/'+name.removeprefix('fonts/');assert digest(data)==expected[relative]
                with TTFont(io.BytesIO(data)) as font:
                    assert font['name'].getDebugName(1) in ('LihuiT','zayJu') and font['name'].getDebugName(2)=='Regular'
                    assert font['name'].getDebugName(5)=='Version '+a.version and font['name'].getDebugName(13)==entries['OFL.txt'].decode().strip()
                    assert len(font.getBestCmap())==810 and len(font.getGlyphOrder())==986
                    assert font['OS/2'].usWeightClass==400 and font['post'].italicAngle==0
                fonts_checked+=1
            if kind=='Website':
                fm=json.loads(entries['font-manifest.json']);assert fm['version']==a.version and len(fm['fonts'])==2
                for r in fm['fonts']:assert digest(entries[r['file']])==r['sha256']
                html=entries['index.html'].decode();assert f'/v{a.version}/' in html and '16 STYLES' not in html
            counts[kind]=len(font_files)
    print(json.dumps({'passed':True,'version':a.version,'commit':a.commit,'assets':7,'archive_fonts':counts,'font_occurrences_checked':fonts_checked,'scope':'all downloaded bytes, internal checksums, exact official font inventory, metadata, source commit and website links'},indent=2))
if __name__=='__main__':main()
