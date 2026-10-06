#!/usr/bin/env python3
"""Prepare only the approved Regular website from exact current build outputs."""
import json,shutil
from pathlib import Path
from fontTools.ttLib import TTFont
from release_support import ROOT,DIST,FAMILIES,read_build,sha

def main():
    report=read_build();site=ROOT/'site';records=[];css=['/* Actual approved Regular faces only. OFL 1.1; see OFL.txt and ATTRIBUTION.txt. */'];cmap=None
    expected={f'{f}/{f}-Regular.woff2' for f in FAMILIES}
    old={p.relative_to(site/'fonts').as_posix() for p in (site/'fonts').glob('*/*') if p.is_file()}
    if old-expected:raise ValueError('Stale website font files; prepare in a clean checkout, never publish mixed old weights')
    for family in FAMILIES:
        source=DIST/'woff2'/family/f'{family}-Regular.woff2'
        with TTFont(source) as f:
            assert f['name'].getDebugName(16)==family and f['OS/2'].usWeightClass==400 and f['post'].italicAngle==0
            current=f.getBestCmap()
            if cmap is not None and current!=cmap:raise ValueError('Per-family coverage differs')
            cmap=current
        target=site/'fonts'/family/source.name;target.parent.mkdir(parents=True,exist_ok=True)
        if target.is_symlink():raise ValueError('Refusing destination symlink')
        shutil.copyfile(source,target);url=target.relative_to(site).as_posix()
        css.append(f'@font-face{{font-family:"{family}";src:url("{url}") format("woff2");font-weight:400;font-style:normal;font-display:block;}}')
        records.append({'file':url,'family':family,'weight':400,'style':'normal','sha256':sha(target)})
    (site/'fonts.css').write_text('\n'.join(css)+'\n')
    (site/'characters.json').write_text(json.dumps([{'unicode':f'U+{cp:04X}','character':chr(cp),'glyph':n} for cp,n in sorted(cmap.items())],ensure_ascii=True,indent=2)+'\n')
    (site/'font-manifest.json').write_text(json.dumps({'version':report['version'],'state':'release','license':'OFL-1.1','source':'https://github.com/SheathedSharp/oh-my-font','author':'zayju','scope':'two Regular 400 upright faces; no synthetic weights','fonts':records},indent=2)+'\n')
    for notice in ('OFL.txt','ATTRIBUTION.txt','AUTHORS.txt','FONTLOG.txt','LICENSE.md'):shutil.copyfile(ROOT/notice,site/notice)
    print('Prepared 2 exact Regular WOFF2s and 810 character entries; no deployment.')
if __name__=='__main__':main()
