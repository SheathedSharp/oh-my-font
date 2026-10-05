#!/usr/bin/env python3
"""Package only exact, verified, licensed outputs; never publishes by itself."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NOTICES = ('OFL.txt', 'ATTRIBUTION.txt', 'AUTHORS.txt', 'FONTLOG.txt', 'LICENSE.md')

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def archive(path: Path, prefix: str, entries: dict[str, bytes]) -> None:
    index = ''.join(f'{sha(data)}  {name}\n' for name, data in sorted(entries.items()))
    entries = dict(entries, **{'SHA256SUMS.txt': index.encode()})
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(entries.items()):
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            info = zipfile.ZipInfo(prefix+'/'+name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name, data in entries.items():
            assert z.read(prefix+'/'+name) == data

def main() -> None:
    version = (ROOT/'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d{3}', version):
        raise SystemExit('Use an explicit OpenType-compatible version such as 0.301.')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise SystemExit('Commit all source/document changes before packaging.')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    checks = json.loads((ROOT/'.release-work/candidate-checks.json').read_text())
    fb = json.loads((ROOT/'.release-work/fontbakery-summary.json').read_text())
    if len(checks['records']) != 96 or not all(r['ots_exit']==0 and r.get('shaping_passed')==15 for r in checks['records']):
        raise SystemExit('Exact-candidate OTS / shaping checks not complete.')
    if len(fb) != 4 or not all(r['scoped_release_gate']=='passed' for r in fb):
        raise SystemExit('FontBakery scoped gate not complete; inspect the full raw results.')
    qa_path = ROOT/f'docs/qa/release-{version}.json'
    qa = json.loads(qa_path.read_text())
    for name, expected in qa['build_inputs_sha256'].items():
        if sha((ROOT/name).read_bytes()) != expected:
            raise SystemExit('Build inputs changed since QA: '+name)
    records=[]
    for row in checks['records']:
        file=ROOT/'dist'/row['file']
        if sha(file.read_bytes()) != row['sha256']:
            raise SystemExit('Changed candidate after checks: '+row['file'])
        records.append({key:row[key] for key in ('file','sha256','family','style','codepoints')})
    source={'repository':'https://github.com/SheathedSharp/oh-my-font','version':version,'tag':'v'+version,'commit':commit,'author':'zayju','license':'OFL-1.1','reserved_font_names':[]}
    shared={name:(ROOT/name).read_bytes() for name in NOTICES}
    shared['SOURCE.json']=(json.dumps(source,indent=2)+'\n').encode()
    readme='''LihuiT / zayJu — version {version}\nBy zayju · https://github.com/SheathedSharp/oh-my-font\n\nFree commercial use under SIL OFL 1.1. Retain the copyright notice,\noriginal-source URL and license when redistributing the Font Software.\nNo compulsory visible credit for ordinary artwork. See ATTRIBUTION.txt.\n\n免费商用，允许修改与再分发。再分发字体时保留版权、原始来源与 OFL 许可。\n普通排版作品不额外强制署名。完整说明见 ATTRIBUTION.txt。\n\n32 static faces / 2 families / 8 weights + upright and 10-degree Oblique.\nNo Han, full Greek/Cyrillic, variable axis or monospaced coding family.\nThe full FontBakery universal profile retains the documented Sigma case\ncoverage finding; ligature caret, math-width and other warnings are not\nrepresented as all-green. See the Release QA report.\n\n{usage}\n'''
    output=ROOT/'release';output.mkdir(exist_ok=True)
    expected=[]
    for fmt in ('TTF','OTF','WOFF2'):
        files=dict(shared)
        for row in records:
            if row['file'].startswith(fmt.lower()+'/'):
                name='fonts/'+row['file'].split('/',1)[1]
                files[name]=(ROOT/'dist'/row['file']).read_bytes()
        usage='Desktop: install TTF OR OTF, not both (same font identities).\nmacOS: select font files and open in Font Book, then Install.\nWindows: select files, right-click Install. Windows is not natively tested.\nLinux: copy to a user font directory and refresh the font cache.'
        if fmt=='WOFF2':
            files['fonts.css']=(ROOT/'site/fonts.css').read_bytes()
            files['example.html']=b'<!doctype html><meta charset="utf-8"><title>LihuiT / zayJu</title><link rel="stylesheet" href="fonts.css"><style>body{padding:5vw;font-family:system-ui}h1{font-family:zayJu;font-weight:700;font-size:clamp(30px,6vw,80px)}p.sample{font-family:LihuiT;font-size:24px}*{font-synthesis:none}</style><h1>Build a brighter tomorrow.</h1><p class="sample">Ideas ship farther. Zayju zayju.de</p><p>By zayju - <a href="ATTRIBUTION.txt">source and attribution</a> - <a href="OFL.txt">OFL 1.1</a></p>'
            usage='Web: link fonts.css from the extracted directory; keep fonts/ beside it.\nExample: <link rel="stylesheet" href="fonts.css">\nUse font-family: "LihuiT" or "zayJu"; font-weight: 100/300/400/500/600/700/800/900;\nfont-style: normal or oblique 10deg. WOFF2 is not a desktop install package.\nPreview example.html using a local HTTP server.'
            urls=re.findall(r'url\("([^\"]+)"\)',files['fonts.css'].decode())
            assert len(urls)==32 and all(url in files for url in urls)
        files['README.txt']=readme.format(version=version,usage=usage).encode()
        name=f'LihuiT-zayJu-v{version}-{fmt}'
        archive(output/(name+'.zip'),name,files);expected.append(name+'.zip')
    files=dict(shared)
    for name in ('index.html','style.css','app.js','fonts.css','characters.json','font-manifest.json'):
        files[name]=(ROOT/'site'/name).read_bytes()
    manifest=json.loads(files['font-manifest.json'])
    assert manifest['license']=='OFL-1.1' and manifest['version']==version
    for row in manifest['fonts']:
        data=(ROOT/'site'/row['file']).read_bytes()
        assert sha(data)==row['sha256']
        matching=next(r for r in records if r['file']=='woff2/'+row['file'][6:])
        assert sha(data)==matching['sha256']
        files[row['file']]=data
    files['README.txt']=readme.format(version=version,usage='Complete static website. Serve this directory over HTTP or deploy unchanged.\nNo external font service, analytics or build step is required.').encode()
    name=f'LihuiT-zayJu-v{version}-Website'
    archive(output/(name+'.zip'),name,files);expected.append(name+'.zip')
    manifest=dict(source,fonts=records,license_sha256=sha(shared['OFL.txt']),build_inputs_sha256=qa['build_inputs_sha256'],qa_scope=qa['scope'])
    (output/'BUILD-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'QA.json').write_bytes(qa_path.read_bytes())
    expected+=['BUILD-MANIFEST.json','QA.json']
    (output/'SHA256SUMS.txt').write_text(''.join(f'{sha((output/name).read_bytes())}  {name}\n' for name in sorted(expected)))
    print(json.dumps({'version':version,'commit':commit,'assets':expected+['SHA256SUMS.txt'],'fonts':len(records)},indent=2))

if __name__=='__main__':
    main()
