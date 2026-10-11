#!/usr/bin/env python3
"""Prepare the 0.500 specimen from the exact current build outputs."""
import json,shutil
from pathlib import Path
from fontTools.ttLib import TTFont
from release_support import ROOT,DIST,FAMILIES,styles,ps_name,read_build,sha,font_path

def main():
    report=read_build();site=ROOT/'site';records=[];css=['/* 32 stored styles. OFL 1.1; see OFL.txt and ATTRIBUTION.txt. Oblique is a 10° slant, not a drawn Italic. */']
    expected={font_path('woff2',family,row['weight'],row['oblique']).split('/',1)[1] for family in FAMILIES for row in styles()}
    font_dir=site/'fonts'
    old={p.relative_to(font_dir).as_posix() for p in font_dir.glob('*/*') if p.is_file()} if font_dir.exists() else set()
    if old-expected:raise ValueError('Stale website font files; prepare in a clean checkout, never publish mixed old weights')
    cmap=None
    for family in FAMILIES:
        for row in styles():
            relative=font_path('woff2',family,row['weight'],row['oblique'])
            source=DIST/relative
            css_style='oblique' if row['oblique'] else 'normal'
            with TTFont(source) as font:
                assert font['name'].getDebugName(16)==family and font['OS/2'].usWeightClass==row['weight']
                assert abs(font['post'].italicAngle-(-10 if row['oblique'] else 0))<0.01
                current=font.getBestCmap()
                if cmap is not None and current!=cmap:raise ValueError('Per-style coverage differs')
                cmap=current
            target=site/'fonts'/family/source.name;target.parent.mkdir(parents=True,exist_ok=True)
            if target.is_symlink():raise ValueError('Refusing destination symlink')
            shutil.copyfile(source,target);url=target.relative_to(site).as_posix()
            css.append(f'@font-face{{font-family:"{family}";src:url("{url}") format("woff2");font-weight:{row["weight"]};font-style:{css_style};font-display:block;}}')
            records.append({'file':url,'family':family,'weight':row['weight'],'style':css_style,'sha256':sha(target)})
    (site/'fonts.css').write_text('\n'.join(css)+'\n')
    (site/'characters.json').write_text(json.dumps([{'unicode':f'U+{cp:04X}','character':chr(cp),'glyph':n} for cp,n in sorted(cmap.items())],ensure_ascii=True,indent=2)+'\n')
    (site/'font-manifest.json').write_text(json.dumps({'version':report['version'],'state':'release-candidate','license':'OFL-1.1','source':'https://github.com/SheathedSharp/oh-my-font','author':'zayju','scope':'32 styles: 8 upright weights and a 10° Oblique of each, for LihuiT and zayJu. Not a variable font. Not a drawn Italic.','fonts':records},indent=2)+'\n')
    for notice in ('OFL.txt','ATTRIBUTION.txt','AUTHORS.txt','FONTLOG.txt','LICENSE.md'):shutil.copyfile(ROOT/notice,site/notice)
    print(f'Prepared {len(records)} WOFF2s and {len(cmap)} character entries; no deployment.')
if __name__=='__main__':main()
