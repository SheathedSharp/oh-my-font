#!/usr/bin/env python3
"""Package only the exact six approved Regular outputs. Never publishes or installs."""
from __future__ import annotations
import hashlib,json,re,subprocess,zipfile
from pathlib import Path
from release_support import ROOT,DIST,WORK,read_build,sha,version
NOTICES=('OFL.txt','ATTRIBUTION.txt','AUTHORS.txt','FONTLOG.txt','LICENSE.md')

def archive(path,prefix,entries):
    entries=dict(entries)
    entries['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name,data in sorted(entries.items())).encode()
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(entries.items()):
            if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe archive member')
            info=zipfile.ZipInfo(prefix+'/'+name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name,data in entries.items():assert z.read(prefix+'/'+name)==data

def main():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise SystemExit('Commit source/docs/QA before packaging')
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();build=read_build();ver=version()
    qa_path=ROOT/'docs/qa'/f'release-{ver}.json';qa=json.loads(qa_path.read_text())
    if qa['version']!=ver or qa['build_inputs_sha256']!=build['source_inputs_sha256']:raise ValueError('Stale QA input record')
    expected={r['file']:r['sha256'] for r in build['records']}
    if {r['file']:r['sha256'] for r in qa['candidates']['records']}!=expected or not qa['candidates']['passed']:raise ValueError('Missing exact candidate checks')
    if not qa['fontbakery']['passed'] or not qa['reproducibility']['passed'] or not qa['unit_tests']['passed']:raise ValueError('Incomplete release gates')
    source={'repository':'https://github.com/SheathedSharp/oh-my-font','version':ver,'tag':'v'+ver,'commit':commit,'author':'zayju','license':'OFL-1.1','reserved_font_names':[],
            'faces':2,'styles':['Regular'],'weight':400,'codepoints_per_face':810,'glyphs_per_face':986,'approved_design_commit':build['approved_commit']}
    common={name:(ROOT/name).read_bytes() for name in NOTICES};common['SOURCE.json']=(json.dumps(source,indent=2)+'\n').encode()
    readme=f'''LihuiT / zayJu {ver} — approved complete redesign\nBy zayju · https://github.com/SheathedSharp/oh-my-font\n\nTwo Regular 400 upright faces. Each: 810 codepoints / 986 glyphs.\nTTF and OTF have the same font identities: install ONE format, not both.\nDeactivate older LihuiT/zayJu versions before installing, to avoid font-cache\nconflicts or accidentally mixing the old 0.301 designs with this redesign.\nOther weights and Obliques are NOT included or synthesized.\n\n本次发布已验收的两款 Regular 400 正体。各 810 编码 / 986 字形。\n安装前请停用旧版本；TTF 与 OTF 只选一种。其他字重和斜体未包含。\n\nSIL OFL 1.1. Retain copyright, original-source notice and OFL when redistributing\nthe Font Software; ordinary artwork does not require compulsory visible credit.\nThe existing Sigma case-coverage finding and FontBakery warnings remain in QA.\nThis is not full Greek/Cyrillic/Han, a variable font or a monospaced coding family.\n\n'''
    out=ROOT/'release';out.mkdir(exist_ok=True);assets=[]
    for fmt in ('ttf','otf','woff2'):
        files=dict(common)
        for row in build['records']:
            if row['format']==fmt:files['fonts/'+row['file'].split('/',1)[1]]=(DIST/row['file']).read_bytes()
        usage='Desktop: install TTF OR OTF. No font is automatically installed.\n'
        if fmt=='woff2':
            files['fonts.css']=(ROOT/'site/fonts.css').read_bytes()
            files['example.html']=b'<!doctype html><meta charset="utf-8"><title>LihuiT / zayJu</title><link rel="stylesheet" href="fonts.css"><style>body{padding:5vw;font-family:system-ui}h1{font-family:zayJu;font-weight:400;font-size:clamp(28px,6vw,72px)}p{font-family:LihuiT;font-weight:400;font-size:24px}*{font-synthesis:none}</style><h1>Build a brighter tomorrow.</h1><p>Ideas ship farther.</p><a href="ATTRIBUTION.txt">Source and attribution</a>'
            assert all(url in files for url in re.findall(r'url\("([^"]+)"\)',files['fonts.css'].decode()))
            usage='Web only. Link fonts.css; use font-family LihuiT or zayJu, font-weight:400, font-style:normal, font-synthesis:none. Serve over HTTP.\n'
        files['README.txt']=(readme+usage).encode();prefix=f'LihuiT-zayJu-v{ver}-{fmt.upper()}';archive(out/(prefix+'.zip'),prefix,files);assets.append(prefix+'.zip')
    site=ROOT/'site';files=dict(common)
    for name in ('index.html','app.js','style.css','fonts.css','characters.json','font-manifest.json','favicon.ico'):files[name]=(site/name).read_bytes()
    for path in (site/'assets').rglob('*'):
        if path.is_file():files[path.relative_to(site).as_posix()]=path.read_bytes()
    manifest=json.loads(files['font-manifest.json']);assert manifest['version']==ver and len(manifest['fonts'])==2
    for face in manifest['fonts']:
        path=site/face['file'];assert sha(path)==face['sha256']==expected['woff2/'+face['file'].removeprefix('fonts/')];files[face['file']]=path.read_bytes()
    files['README.txt']=(readme+'Complete static website. Serve over HTTP or deploy unchanged.\n').encode()
    prefix=f'LihuiT-zayJu-v{ver}-Website';archive(out/(prefix+'.zip'),prefix,files);assets.append(prefix+'.zip')
    manifest={**source,'fonts':build['records'],'build_inputs_sha256':build['source_inputs_sha256'],'qa_scope':qa['scope']}
    (out/'BUILD-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');(out/'QA.json').write_bytes(qa_path.read_bytes());assets+=['BUILD-MANIFEST.json','QA.json']
    (out/'SHA256SUMS.txt').write_text(''.join(f'{sha(out/name)}  {name}\n' for name in sorted(assets)));assets+=['SHA256SUMS.txt']
    actual={p.name for p in out.iterdir() if p.is_file()}
    if actual!=set(assets):raise ValueError('Unexpected stale assets in release directory')
    print(json.dumps({'version':ver,'commit':commit,'branch':branch,'assets':assets,'fonts':6,'faces':2},indent=2))
if __name__=='__main__':main()
