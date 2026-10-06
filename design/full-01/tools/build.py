#!/usr/bin/env python3
"""Compile the completed reference cuts from editable UFOs, without drawing synthesis.

The source is the requested family's UFO. ufo2ft handles standard composite,
anchor, feature and outline conversion; no legacy outline input or weights are
created. Font identities are development-only and never replace installed fonts.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,os
from pathlib import Path
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from ufoLib2 import Font
import ufo2ft
ROOT=Path(__file__).resolve().parents[3];FULL=ROOT/'design/full-01'
FAMILIES=('LihuiT','zayJu');CORE='BMRage23689';OUT=ROOT/'.release-work/full-01'
EPOCH=3874089600

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def signature(u,name):
    p=DecomposingRecordingPen(u);u[name].draw(p)
    return (u[name].width,p.value)

def verify_approved_core(u,family):
    manifest=json.loads((FULL/'approved-core.json').read_text())
    for name,expected in manifest['files'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Approved core snapshot changed: '+name)
    core=Font.open(ROOT/'design/core-01/sources'/f'{family}-Core01.ufo')
    for c in CORE:
        name=next(g.name for g in core if ord(c) in g.unicodes)
        if signature(u,name)!=signature(core,name):raise ValueError(f'Approved {family}/{name} shape or advance changed')

def load(family):
    u=Font.open(FULL/'sources'/f'{family}-Reference.ufo');verify_approved_core(u,family);return u

def compile_font(u,cff=False):
    # Same-family standard OpenType compilation, not a font design generator.
    common=dict(useProductionNames=False,removeOverlaps=True,overlapsBackend='pathops',inplace=False)
    if cff:f=ufo2ft.compileOTF(u,optimizeCFF=0,**common)
    else:f=ufo2ft.compileTTF(u,cubicConversionError=.0002,**common)
    f['head'].created=EPOCH;f['head'].modified=EPOCH;f.recalcTimestamp=False
    return f

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=OUT)
    p.add_argument('--partial',action='store_true',help='Drawing preview only; does not satisfy full-coverage QA')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);records=[]
    target=json.loads((FULL/'repertoire.json').read_text())
    for family in FAMILIES:
        u=load(family);cmap={cp:g.name for g in u for cp in g.unicodes}
        if not a.partial:
            missing=set(map(int,target['cmap']))-set(cmap)
            names=set(target['glyph_order'])-set(u.keys())
            if missing or names:raise ValueError(f'{family}: {len(missing)} missing codepoints, {len(names)} missing feature glyphs')
        for fmt in ('ttf','otf','woff2'):
            f=compile_font(u,fmt=='otf');f.flavor='woff2' if fmt=='woff2' else None
            path=a.output/'fonts'/f'{family}FullDraft-Reference.{fmt}';path.parent.mkdir(parents=True,exist_ok=True);f.save(path)
            with TTFont(path,checkChecksums=2) as checked:
                if checked.getBestCmap()!=cmap:raise ValueError('cmap changed at export')
                for tag in checked.keys():
                    if tag!='GlyphOrder':checked.getTableData(tag)
            records.append({'file':path.relative_to(a.output).as_posix(),'family':family,'format':fmt,'glyphs':len(u),'codepoints':len(cmap),'sha256':sha(path)})
            print('Built',path.name,len(u),'glyphs',flush=True)
    inputs=[FULL/'approved-core.json',FULL/'repertoire.json',*sorted((FULL/'sources').rglob('*')),*sorted((FULL/'tools').glob('*.py'))]
    report={'stage':'partial-drawing-preview' if a.partial else 'full-reference-review','additional_weights':False,'records':records,
            'source_inputs':{path.relative_to(ROOT).as_posix():sha(path) for path in inputs if path.is_file()}}
    (a.output/'build.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
