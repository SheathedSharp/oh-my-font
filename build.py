#!/usr/bin/env python3
"""Build the 0.500 family from approved Regular drawings and stored masters.

Regular 400 upright is compiled from the hash-locked 0.400 UFO. Every other
upright weight and every Oblique is compiled from its own UFO master. This
command does not interpolate, buffer, or import src/outlines.py. It does not
install or publish fonts.
"""
from __future__ import annotations
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'tools'))
from release_support import (ROOT,DIST,FAMILIES,FORMATS,WEIGHT_NAMES,PANOSE_WEIGHT,FILE_COUNT,reference,
    validate_approval,source_hashes,expected_files,version,sha,styles,ps_name,legacy_names,font_path,master_path)
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.otlLib.builder import buildStatTable
from fontTools.pens.recordingPen import DecomposingRecordingPen
from ufo2ft.filters.decomposeTransformedComponents import DecomposeTransformedComponentsFilter
from ufoLib2 import Font
import ufo2ft

def geometry_signature(font,name):
    glyphs=font.getGlyphSet();pen=DecomposingRecordingPen(glyphs);glyphs[name].draw(pen)
    return (font['hmtx'].metrics[name],pen.value)

def compile_style(ufo,cff,remove_overlaps):
    """Regular 400 upright uses the hash-locked compiler. Other masters do not.

    Their contours are already simple. Pathops overlap removal puts rounding
    knots back, so those styles compile with removal off. Timestamps, gasp and
    prep match the approved compiler.
    """
    if remove_overlaps:
        return reference.compile_font(ufo,cff)
    common=dict(useProductionNames=False,removeOverlaps=False,overlapsBackend='pathops',inplace=False)
    if cff:
        font=ufo2ft.compileOTF(ufo,optimizeCFF=0,**common)
    else:
        font=ufo2ft.compileTTF(ufo,cubicConversionError=.0002,flattenComponents=True,
                               filters=[DecomposeTransformedComponentsFilter(pre=True)],**common)
        gasp=newTable('gasp');gasp.gaspRange={65535:15};font['gasp']=gasp
        prep=newTable('prep');prep.program=Program()
        prep.program.fromAssembly(['PUSHW[]','511','SCANCTRL[]','PUSHB[]','4','SCANTYPE[]'])
        font['prep']=prep;font['maxp'].maxStackElements=max(1,font['maxp'].maxStackElements)
    font['head'].created=reference.EPOCH;font['head'].modified=reference.EPOCH;font.recalcTimestamp=False
    return font

def load_style(family,weight,oblique):
    if weight==400 and not oblique:
        return reference.load(family)
    path=master_path(family,weight,oblique)
    if path is None or not path.is_dir():raise ValueError(f'Missing stored master for {family} {weight} oblique={oblique}')
    ufo=Font.open(path)
    reference.validate_source(ufo)
    if ufo.info.openTypeOS2WeightClass!=weight:raise ValueError(f'Master weight class mismatch: {path.name}')
    if abs((ufo.info.italicAngle or 0)-(-10 if oblique else 0))>0.01:raise ValueError(f'Master italic angle mismatch: {path.name}')
    return ufo

def promote(font,family,weight=400,oblique=False):
    if family not in FAMILIES or weight not in WEIGHT_NAMES:raise ValueError('Unknown style')
    before={n:geometry_signature(font,n) for n in font.getGlyphOrder()}
    layout={t:font.getTableData(t) for t in ('cmap','GDEF','GSUB','GPOS','hmtx')}
    ver=version();post=ps_name(family,weight,oblique)
    legacy_family,legacy_style,typo_family,typo_style=legacy_names(family,weight,oblique)
    angle=-10 if oblique else 0
    if oblique:
        drawing='10° Oblique of this weight’s master, with counter shear reduced and apertures opened. Not a separately drawn Italic.'
    elif weight==400:
        drawing='Upright outlines are the owner-approved 0.400 Regular drawings, unchanged.'
    else:
        drawing='Upright master with its own stem, join, counter and review-glyph proportions, drawn from the approved 0.400 Regular.'
    description=(f'{family} {typo_style}. {drawing} 810 codepoints, 986 glyphs. Latin-limited; not a variable font. '
                 'Do not mix with the 0.301 family.')
    values={1:legacy_family,2:legacy_style,3:f'{ver};zayj;{post}',4:f'{family} {typo_style}',5:'Version '+ver,6:post,
            16:typo_family,17:typo_style,10:description,
            11:'https://github.com/SheathedSharp/oh-my-font',9:'zayju',12:'https://github.com/SheathedSharp',
            0:(ROOT/'OFL.txt').read_text().splitlines()[0],13:(ROOT/'OFL.txt').read_text().strip(),14:'https://openfontlicense.org'}
    for name_id,text in values.items():
        font['name'].removeNames(nameID=name_id)
        font['name'].setName(text,name_id,3,1,0x409)
    font['head'].fontRevision=float(ver);font.recalcTimestamp=False
    font['OS/2'].usWeightClass=weight
    font['OS/2'].usWidthClass=5
    # Shared clip box. Measured across every master, including Oblique.
    # Typo/hhea line spacing stays the approved Regular values.
    font['OS/2'].usWinAscent=1388
    font['OS/2'].usWinDescent=626
    font['OS/2'].panose.bWeight=PANOSE_WEIGHT[weight]
    selection=font['OS/2'].fsSelection & ~0b1001100001
    if weight==700:selection|=1<<5
    elif not oblique:selection|=1<<6
    if oblique:selection|=(1<<0)|(1<<9)
    font['OS/2'].fsSelection=selection
    font['head'].macStyle=(1 if weight==700 else 0)|(2 if oblique else 0)
    font['post'].italicAngle=angle
    if oblique:
        font['hhea'].caretSlopeRise=1000;font['hhea'].caretSlopeRun=176
    else:
        font['hhea'].caretSlopeRise=1;font['hhea'].caretSlopeRun=0
    if 'CFF ' in font:
        cff=font['CFF '].cff;cff.fontNames=[post];top=cff.topDictIndex[0]
        top.FullName=f'{family} {typo_style}';top.FamilyName=family;top.Weight=WEIGHT_NAMES[weight];top.version=ver
    # Axis value "Oblique" is the design name. The registered ital axis itself is called Italic.
    buildStatTable(font,[
        dict(tag='wght',name='Weight',ordering=0,values=[dict(value=weight,name=WEIGHT_NAMES[weight],flags=0x2 if weight==400 else 0)]),
        dict(tag='ital',name='Italic',ordering=1,values=[dict(value=1 if oblique else 0,name='Oblique' if oblique else 'Upright',flags=0x2 if not oblique else 0)]),
    ],elidedFallbackName=2,macNames=False)
    if any(geometry_signature(font,n)!=value for n,value in before.items()):raise ValueError('Identity promotion altered glyphs')
    if any(font.getTableData(t)!=data for t,data in layout.items()):raise ValueError('Identity promotion altered layout/metrics')
    return font

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=DIST)
    args=parser.parse_args();dest=args.output.resolve();validate_approval();started=time.monotonic()
    if args.output.is_symlink():raise ValueError('Refusing symlink output directory')
    dest.mkdir(parents=True,exist_ok=True)
    existing={p.relative_to(dest).as_posix() for fmt in FORMATS for p in (dest/fmt).glob('*/*') if p.is_file()}
    if existing-expected_files():raise ValueError('Old/unknown font files in output. Use a fresh --output directory; no silent mixing.')
    records=[]
    for family in FAMILIES:
        for row in styles():
            ufo=load_style(family,row['weight'],row['oblique'])
            for fmt in FORMATS:
                font=promote(compile_style(ufo,fmt=='otf',row['weight']==400 and not row['oblique']),family,row['weight'],row['oblique'])
                font.flavor='woff2' if fmt=='woff2' else None
                relative=font_path(fmt,family,row['weight'],row['oblique'])
                path=dest/relative;path.parent.mkdir(parents=True,exist_ok=True)
                if path.is_symlink():raise ValueError('Refusing output symlink')
                font.save(path)
                with TTFont(path,checkChecksums=2) as checked:
                    if len(checked.getGlyphOrder())!=986 or len(checked.getBestCmap())!=810:raise ValueError('Incomplete candidate: '+relative)
                    for tag in checked.keys():
                        if tag!='GlyphOrder':checked.getTableData(tag)
                    features=sorted({rec.FeatureTag for tag in ('GSUB','GPOS') for rec in checked[tag].table.FeatureList.FeatureRecord})
                records.append({'file':relative,'family':family,'style':row['style'],'weight':row['weight'],'oblique':row['oblique'],'format':fmt,
                                'glyphs':986,'codepoints':810,'bytes':path.stat().st_size,'features':features,'sha256':sha(path),'structural_check':'passed'})
                print('Built',relative,flush=True)
    report={'project':'LihuiT / zayJu','version':version(),'scope':'multiweight-0500','files':FILE_COUNT,'families':2,'styles':len(styles()),'faces':FILE_COUNT//len(FORMATS),
            'approved_commit':'4640e2b38bc20b72e4f5584113208fa819b5adc9','source_inputs_sha256':source_hashes(),
            'regular_400_upright_preserves_approved_outlines':True,'other_styles_compile_stored_masters':True,
            'oblique_is_not_a_separately_drawn_italic':True,'records':records,'seconds':round(time.monotonic()-started,3)}
    (dest/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Complete: 2 families × 16 styles / {FILE_COUNT} files. No installation or publication.')
if __name__=='__main__':main()
