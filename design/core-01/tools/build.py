#!/usr/bin/env python3
"""Compile the 11-glyph design studies from their authoritative UFO drawings.

No interpolation, shared stroke recipes, tracing, old-font imports, or synthetic
weights. Outputs have unique study names and are never installed or published.
The .glyphs companion is exported from the UFO; edits must have one authority.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.roundingPen import RoundingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.misc.roundTools import otRound
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont
from ufoLib2 import Font
import glyphsLib
import ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument, SourceDescriptor
from datetime import datetime

STUDY=Path(__file__).resolve().parents[1];ROOT=STUDY.parents[1]
CORE='BMRage23689';FAMILIES=('LihuiT','zayJu');EPOCH=3874089600


def load_source(family):
    u=Font.open(STUDY/'sources'/f'{family}-Core01.ufo')
    cmap={cp:g.name for g in u for cp in g.unicodes}
    if set(cmap)!=set(map(ord,CORE+' ')) or len(u)!=13:
        raise ValueError('Scope drift: exactly 11 core characters + space/.notdef required')
    if u.info.familyName!=family+' Core Study 01':raise ValueError('Study identity mismatch')
    if any(g.components for g in u):raise ValueError('Core glyphs must have their own editable outlines')
    return u,cmap


def compile_source(u,cmap,cff=False):
    order=u.lib['public.glyphOrder'];fb=FontBuilder(1000,isTTF=not cff)
    fb.setupGlyphOrder(order);fb.setupCharacterMap(cmap)
    outlines={};metrics={}
    for name in order:
        g=u[name]
        if cff:
            pen=T2CharStringPen(g.width,None,roundTolerance=0)
            target=RoundingPen(pen,roundFunc=lambda v:otRound(v*64)/64)
            g.draw(target);outlines[name]=pen.getCharString()
            b=BoundsPen(None);g.draw(RoundingPen(b,roundFunc=lambda v:otRound(v*64)/64))
            lsb=otRound(b.bounds[0]) if b.bounds else 0
        else:
            pen=TTGlyphPen(None)
            g.draw(ReverseContourPen(Cu2QuPen(pen,max_err=.2)))
            outlines[name]=pen.glyph();outlines[name].recalcBounds(None)
            lsb=getattr(outlines[name],'xMin',0)
        metrics[name]=(otRound(g.width),lsb)
    name=u.info.familyName;ps=name.replace(' ','')+'-Reference'
    if cff:fb.setupCFF(ps,{'FullName':name+' Reference','FamilyName':name,'Weight':'Regular','version':'0.001'},outlines,{})
    else:fb.setupGlyf(outlines)
    fb.setupHorizontalMetrics(metrics);fb.setupHorizontalHeader(ascent=900,descent=-300,lineGap=0)
    fb.setupNameTable({'familyName':name,'styleName':'Reference','typographicFamily':name,'typographicSubfamily':'Reference',
        'fullName':name+' Reference','psName':ps,'uniqueFontIdentifier':'Core01;'+ps,'version':'Version 0.001; DESIGN STUDY — NOT A RELEASE',
        'copyright':u.info.copyright,'designer':'zayju','designerURL':'https://github.com/SheathedSharp',
        'vendorURL':'https://github.com/SheathedSharp/oh-my-font','licenseDescription':(ROOT/'OFL.txt').read_text().strip(),
        'licenseInfoURL':'https://openfontlicense.org',
        'description':'Unapproved design study. Only B M R a g e 2 3 6 8 9 and space. No full-family, multi-weight or italic claim.'})
    fb.setupOS2(version=4,usWeightClass=400,usWidthClass=5,fsType=0,fsSelection=0xC0,
        sTypoAscender=900,sTypoDescender=-300,sTypoLineGap=0,usWinAscent=900,usWinDescent=300,
        sxHeight=round(u.info.xHeight),sCapHeight=round(u.info.capHeight),achVendID='zayj')
    fb.setupPost(italicAngle=0,underlinePosition=-110,underlineThickness=45);fb.setupMaxp()
    f=fb.font;f['head'].created=EPOCH;f['head'].modified=EPOCH;f['head'].fontRevision=.001;f.recalcTimestamp=False
    fea=['languagesystem DFLT dflt;','languagesystem latn dflt;','feature kern {']
    for (a,b),value in sorted(u.kerning.items()):fea.append(f'pos {a} {b} {round(value)};')
    fea.append('} kern;');addOpenTypeFeaturesFromString(f,'\n'.join(fea))
    return f,ps


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'.release-work/core-01')
    p.add_argument('--export-glyphs',action='store_true',help='Export UFO-derived companion; do not edit both formats independently')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    records=[]
    for family in FAMILIES:
        u,cmap=load_source(family)
        if args.export_glyphs:
            ds=DesignSpaceDocument();source=SourceDescriptor()
            source.font=u;source.path=str(u.path);source.name=family+'Reference'
            source.familyName=u.info.familyName;source.styleName=u.info.styleName;source.location={}
            ds.addSource(source)
            companion=glyphsLib.to_glyphs(ds,ufo_module=ufoLib2);companion.date=datetime(2026,10,6)
            with (STUDY/'sources'/f'{family}-Core01.glyphs').open('w',encoding='utf-8') as output:
                glyphsLib.dump(companion,output)
        for fmt in ('ttf','otf','woff2'):
            f,ps=compile_source(u,cmap,fmt=='otf');f.flavor='woff2' if fmt=='woff2' else None
            path=args.output/'fonts'/(ps+'.'+fmt);path.parent.mkdir(parents=True,exist_ok=True);f.save(path)
            with TTFont(path,checkChecksums=2) as check:
                if set(check.getBestCmap())!=set(cmap):raise ValueError('Encoded repertoire changed')
                for tag in check.keys():
                    if tag!='GlyphOrder':check.getTableData(tag)
            records.append({'file':path.relative_to(args.output).as_posix(),'family':family,'format':fmt,'glyphs':13,'codepoints':12,
                            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
    source_hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((STUDY/'sources').rglob('*')) if p.is_file()}
    report={'scope':'core study only, 11 glyphs per family, unapproved','sources':source_hashes,'records':records}
    (args.output/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Compiled two isolated 11-glyph studies:',len(records),'files; no installation or publication.')
if __name__=='__main__':main()
