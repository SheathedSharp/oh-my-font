#!/usr/bin/env python3
"""Build local desktop and web fonts from original LihuiT/zayJu outline source.

Python 3.10+. Uses only declared dependencies, never reads an installed font.
The program writes into --output; it never installs fonts or modifies the OS.
"""
from __future__ import annotations
import argparse, hashlib, json, logging, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
try:
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.pens.t2CharStringPen import T2CharStringPen
    from fontTools.ttLib import TTFont,newTable
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    from fontTools.otlLib.builder import buildStatTable
    from fontTools.ttLib.tables.O_S_2f_2 import Panose
    from outlines import Designer, WEIGHTS, UPM, draw_geometry
    from features import build_features
except ImportError as e:
    raise SystemExit('Missing build dependency. Run: python -m pip install -r requirements.txt\n'+str(e))

VERSION='0.301'
EPOCH=3874089600 # Fixed OpenType timestamp: reproducible builds, not wall-clock time.

def compile_font(d:Designer, cff:bool=False):
    fb=FontBuilder(UPM,isTTF=not cff)
    names=list(d.glyphs)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(d.cmap)
    metrics={}
    glyphs={}
    for n,g in d.glyphs.items():
        pen=T2CharStringPen(g.advance,None) if cff else TTGlyphPen(None)
        draw_geometry(g.geometry,pen)
        glyphs[n]=pen.getCharString(private=None,globalSubrs=None) if cff else pen.glyph()
        # Glyph drawing is rounded; hmtx bearing uses the same rounding convention.
        xmin=round(g.geometry.bounds[0]) if not g.geometry.is_empty else 0
        metrics[n]=(g.advance,xmin)
    weightname=WEIGHTS[d.weight]
    sub=('Oblique' if d.weight==400 else weightname+' Oblique') if d.oblique else weightname
    post=d.family+'-'+sub.replace(' ','')
    if cff:
        fb.setupCFF(post,{'FullName':d.family+' '+sub,'FamilyName':d.family,'Weight':weightname,
                         'version':VERSION,'ItalicAngle':-10 if d.oblique else 0,
                         'UnderlinePosition':-115,'UnderlineThickness':50},glyphs,{})
    else:fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=1000,descent=-300,lineGap=0,
                             caretSlopeRise=1000,caretSlopeRun=176 if d.oblique else 0)
    legacy_family=d.family if d.weight in [400,700] else d.family+' '+weightname
    legacy_sub=('Bold' if d.weight==700 else '')+(' Italic' if d.oblique else '')
    legacy_sub=legacy_sub.strip() or 'Regular'
    copyright_note='Copyright 2026 zayju. LihuiT + zayJu. Attribution specified by the project owner; see RIGHTS.zh-CN.md.'
    namesdict={
      'familyName':legacy_family,'styleName':legacy_sub,'uniqueFontIdentifier':f'{VERSION};zayj;{post}',
      'fullName':d.family+' '+sub,'psName':post,'version':'Version '+VERSION,
      'typographicFamily':d.family,'typographicSubfamily':sub,
      'manufacturer':'zayju','designer':'zayju','designerURL':'https://github.com/SheathedSharp',
      'description':'Reference-led reconstruction 0.301. Paired geometric sans-serif: '+('text cut' if d.text else 'display cut')+'. Static development build. No CJK coverage. '+('10-degree oblique, not a separately drawn italic.' if d.oblique else 'Upright.'),
      'vendorURL':'https://github.com/SheathedSharp','copyright':copyright_note,
      'licenseDescription':'Project source deliverable; no third-party font outlines included. See RIGHTS.zh-CN.md. No legal clearance or exclusive-rights warranty is asserted.'}
    fb.setupNameTable(namesdict)
    fb.font['name'].setName('Ideas into real software. Build a brighter tomorrow.',19,3,1,0x409)
    # Chinese names are metadata, not a claim to include Chinese glyphs.
    cname=d.family
    fb.font['name'].setName(cname,16,3,1,0x804)
    fb.font['name'].setName(sub,17,3,1,0x804)
    bold=d.weight==700
    flags=(1<<7)|(1<<8)|((1<<5) if bold else 0)|((1<<0)|(1<<9) if d.oblique else 0)|((1<<6) if not bold and not d.oblique else 0)
    p=Panose();p.bFamilyType=2;p.bSerifStyle=11;p.bWeight={100:2,300:3,400:5,500:6,600:7,700:8,800:9,900:10}[d.weight]
    p.bProportion=3;p.bContrast=2;p.bStrokeVariation=2;p.bArmStyle=3;p.bLetterForm=2 if d.oblique else 1;p.bMidline=2;p.bXHeight=4
    fb.setupOS2(version=4,usWeightClass=d.weight,usWidthClass=5,fsType=0,fsSelection=flags,
                sTypoAscender=1000,sTypoDescender=-300,sTypoLineGap=0,usWinAscent=1360,usWinDescent=460,
                sxHeight=d.h,sCapHeight=d.cap,achVendID='zayj',panose=p,
                ySubscriptXSize=570,ySubscriptYSize=570,ySubscriptXOffset=0,ySubscriptYOffset=160,
                ySuperscriptXSize=570,ySuperscriptYSize=570,ySuperscriptXOffset=0,ySuperscriptYOffset=425,
                yStrikeoutSize=max(30,round(d.t*.65)),yStrikeoutPosition=320)
    fb.setupPost(italicAngle=-10 if d.oblique else 0,underlinePosition=-115,underlineThickness=50,isFixedPitch=0)
    fb.setupMaxp()
    font=fb.font
    font['OS/2'].recalcCodePageRanges(font)
    font['head'].fontRevision=float(VERSION)
    font['head'].macStyle=(1 if bold else 0)|(2 if d.oblique else 0)
    font['head'].created=EPOCH;font['head'].modified=EPOCH
    font.recalcTimestamp=False
    if not cff:
        font['gasp']=newTable('gasp');font['gasp'].gaspRange={65535:15}
        # Scan control for unhinted outlines; this is not glyph hinting.
        from fontTools.ttLib.tables.ttProgram import Program
        prep=newTable('prep');prep.program=Program()
        prep.program.fromAssembly(['PUSHW[]','511','SCANCTRL[]','PUSHB[]','4','SCANTYPE[]'])
        font['prep']=prep
        font['maxp'].maxStackElements=max(1,font['maxp'].maxStackElements)
    features=build_features(d)
    addOpenTypeFeaturesFromString(font,features)
    buildStatTable(font,[{'tag':'wght','name':'Weight','ordering':0,'values':[{'value':d.weight,'name':weightname,'flags':2 if d.weight==400 else 0}]},
                         {'tag':'ital','name':'Italic','ordering':1,'values':[{'value':1 if d.oblique else 0,'name':'Oblique' if d.oblique else 'Roman','flags':0 if d.oblique else 2, **({} if d.oblique else {'linkedValue':1})}]}])
    # Modern macOS reads Unicode/Windows name records; omit legacy Mac Roman duplicates.
    font['name'].names=[record for record in font['name'].names if record.platformID!=1]
    return font,post,features

def check_font(path:Path):
    """Deterministic structural checks, not a replacement for real-device testing."""
    with TTFont(path,checkChecksums=2) as f:
        cmap=f.getBestCmap()
        for name_id, expected in [(8,'zayju'),(9,'zayju'),(11,'https://github.com/SheathedSharp'),(12,'https://github.com/SheathedSharp')]:
            if f['name'].getDebugName(name_id)!=expected:raise ValueError(f'Incorrect metadata name ID {name_id}')
        required=['head','hhea','hmtx','maxp','name','OS/2','cmap','post','GSUB','GPOS','GDEF','STAT']
        missing=[t for t in required if t not in f]
        if missing:raise ValueError(f'{path.name}: missing tables {missing}')
        if len(cmap)<500:raise ValueError('Unexpectedly incomplete character map')
        for cp in range(32,127):
            if cp not in cmap:raise ValueError(f'ASCII gap: {cp}')
        if 'fvar' in f:raise ValueError('Static builds must not pretend to be variable')
        for n in f.getGlyphOrder():
            if f['hmtx'][n][0]<0:raise ValueError('Negative advance: '+n)
        digit_widths=[f['hmtx'][n+'.tnum'][0] for n in ['zero','one','two','three','four','five','six','seven','eight','nine']]
        if len(set(digit_widths))!=1:raise ValueError('tnum is not tabular')
        # Force decompile/recompile of every OpenType table.
        for tag in f.keys():
            if tag!='GlyphOrder':f.getTableData(tag)
        return {'file':path.name,'glyphs':len(f.getGlyphOrder()),'unicode_codepoints':len(cmap),
                'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'features':sorted(set(rec.FeatureTag for tag in ['GSUB','GPOS'] for rec in f[tag].table.FeatureList.FeatureRecord)),
                'author':f['name'].getDebugName(9),'author_url':f['name'].getDebugName(12),'family':f['name'].getDebugName(16),'style':f['name'].getDebugName(17),'structural_check':'passed'}

def save_font(font, output_path, fmt):
    """Use bounded Brotli effort; this changes compression, never glyph data."""
    font.flavor='woff2' if fmt=='woff2' else None
    if fmt!='woff2':
        font.save(output_path,reorderTables=True)
        return
    from fontTools.ttLib import woff2
    original=woff2.brotli.compress
    def compress(data,**kwargs):
        kwargs.setdefault('quality',8)
        return original(data,**kwargs)
    woff2.brotli.compress=compress
    try:
        font.save(output_path,reorderTables=True)
    finally:
        woff2.brotli.compress=original

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--families',nargs='+',choices=['LihuiT','zayJu'],default=['LihuiT','zayJu'])
    parser.add_argument('--weights',nargs='+',type=int,choices=list(WEIGHTS),default=list(WEIGHTS))
    parser.add_argument('--styles',nargs='+',choices=['upright','oblique'],default=['upright','oblique'])
    parser.add_argument('--formats',nargs='+',choices=['ttf','otf','woff2'],default=['ttf','otf','woff2'])
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    parser.add_argument('--skip-checks',action='store_true',help='Skip post-build structural checks, not font construction')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    records=[];started=time.time()
    for family in args.families:
        for weight in args.weights:
            for style in args.styles:
                d=Designer(family,weight,style=='oblique').build()
                tt=None
                for fmt in args.formats:
                    if fmt=='otf':font,post,fea=compile_font(d,True)
                    else:
                        if tt is None:tt,post,fea=compile_font(d,False)
                        font=tt
                    out=args.output/fmt/family/(post+'.'+fmt);out.parent.mkdir(parents=True,exist_ok=True)
                    save_font(font,out,fmt)
                    records.append(check_font(out) if not args.skip_checks else {'file':out.name,'structural_check':'skipped'})
                    print(f'Built {out.relative_to(args.output)}',flush=True)
                meta=args.output/'metadata'/family;meta.mkdir(parents=True,exist_ok=True)
                (meta/(post+'.fea')).write_text(fea,encoding='utf-8')
                if weight==400 and style=='upright':
                    inventory=[{'unicode':f'U+{cp:04X}','character':chr(cp),'glyph':n} for cp,n in sorted(d.cmap.items()) if cp not in (0,13)]
                    (meta/'characters.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'project':'LihuiT + zayJu','version':VERSION,'files':len(records),'build_seconds':round(time.time()-started,2),
            'platform_installation_tested':False,'real_device_hinting_tested':False,'records':records}
    (args.output/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'\nDone. {len(records)} files in {args.output.resolve()}\nFonts have NOT been installed automatically.')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,RuntimeError) as e:
        logging.error('%s',e);sys.exit(1)
