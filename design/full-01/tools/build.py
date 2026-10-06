#!/usr/bin/env python3
"""Compile the completed reference cuts from editable UFOs, without drawing synthesis.

The source is the requested family's UFO. ufo2ft handles standard composite,
anchor, feature and outline conversion; no legacy outline input or weights are
created. Font identities are development-only and never replace installed fonts.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,os,math
from pathlib import Path
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont,newTable
from fontTools.ttLib.tables.ttProgram import Program
from ufo2ft.filters.decomposeTransformedComponents import DecomposeTransformedComponentsFilter
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
        if name not in u or signature(u,name)!=signature(core,name) or u[name].unicodes!=core[name].unicodes:
            raise ValueError(f'Approved {family}/{name} shape, advance or encoding changed')

def validate_source(u):
    cmap={}
    for g in u:
        if not math.isfinite(g.width) or not 0<=g.width<=65535:raise ValueError('Invalid glyph advance: '+g.name)
        anchors=set()
        for anchor in g.anchors:
            if anchor.name in anchors:raise ValueError('Duplicate glyph anchor: '+g.name)
            anchors.add(anchor.name)
            if not all(math.isfinite(v) for v in (anchor.x,anchor.y)):raise ValueError('Non-finite anchor: '+g.name)
        for contour in g.contours:
            for point in contour.points:
                if not all(math.isfinite(v) for v in (point.x,point.y)):raise ValueError('Non-finite outline: '+g.name)
        for cp in g.unicodes:
            if not isinstance(cp,int) or not 0<=cp<=0x10ffff or 0xd800<=cp<=0xdfff:raise ValueError('Invalid Unicode scalar')
            if cp in cmap:raise ValueError('Duplicate codepoint: '+hex(cp))
            cmap[cp]=g.name
        for component in g.components:
            if component.baseGlyph not in u:raise ValueError('Unknown component: '+component.baseGlyph)
            if not all(math.isfinite(v) for v in component.transformation):raise ValueError('Non-finite component transform')
    visited=set();active=set()
    def visit(name):
        if name in active:raise ValueError('Cyclic component graph: '+name)
        if name in visited:return
        active.add(name)
        for c in u[name].components:visit(c.baseGlyph)
        active.remove(name);visited.add(name)
    for name in u.keys():visit(name)
    return cmap

def load(family):
    if family not in FAMILIES:raise ValueError('Unknown reference family')
    u=Font.open(FULL/'sources'/f'{family}-Reference.ufo')
    validate_source(u);verify_approved_core(u,family)
    return u

def compile_font(u,cff=False):
    # Same-family standard OpenType compilation, not a font design generator.
    common=dict(useProductionNames=False,removeOverlaps=True,overlapsBackend='pathops',inplace=False)
    if cff:f=ufo2ft.compileOTF(u,optimizeCFF=0,**common)
    else:
        # Keep source components editable, but resolve transformed outlines and
        # nested references before integer-grid conversion in the compiler copy.
        # This prevents TTF/CFF disagreement at the OE join without moving the
        # approved core or weakening the geometric error gate.
        f=ufo2ft.compileTTF(u,cubicConversionError=.0002,flattenComponents=True,
                           filters=[DecomposeTransformedComponentsFilter(pre=True)],**common)
        gasp=newTable('gasp');gasp.gaspRange={65535:15};f['gasp']=gasp
        prep=newTable('prep');prep.program=Program()
        prep.program.fromAssembly(['PUSHW[]','511','SCANCTRL[]','PUSHB[]','4','SCANTYPE[]'])
        f['prep']=prep;f['maxp'].maxStackElements=max(1,f['maxp'].maxStackElements)
    f['head'].created=EPOCH;f['head'].modified=EPOCH;f.recalcTimestamp=False
    return f

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=OUT)
    p.add_argument('--partial',action='store_true',help='Drawing preview only; does not satisfy full-coverage QA')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);records=[]
    target=json.loads((FULL/'repertoire.json').read_text())
    for family in FAMILIES:
        u=load(family);cmap=validate_source(u)
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
    inputs=[ROOT/'OFL.txt',FULL/'requirements.txt',ROOT/'design/core-01/requirements.txt',ROOT/'design/core-01/tools/geometry.py',FULL/'approved-core.json',FULL/'repertoire.json',FULL/'helper-glyphs.json',*sorted((FULL/'sources').rglob('*')),*sorted((FULL/'tools').glob('*.py')),*sorted((FULL/'tools').glob('*.html')),*sorted((FULL/'tools').glob('*.swift')),*sorted((FULL/'tests').glob('*.py'))]
    report={'stage':'partial-drawing-preview' if a.partial else 'full-reference-review','additional_weights':False,'records':records,
            'source_inputs':{path.relative_to(ROOT).as_posix():sha(path) for path in inputs if path.is_file()}}
    (a.output/'build.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
