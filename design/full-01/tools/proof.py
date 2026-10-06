#!/usr/bin/env python3
"""Render the actual completed CFF files and an offline editable-source glyph atlas.

The raster glyph atlas uses a temporary in-memory PUA mapping to reach unencoded
feature glyphs by name; this map is never saved as a font or added to the UFO.
The separate HTML displays source vectors, not browser-shaped text or fallback.
"""
from __future__ import annotations
import io,json,math,unicodedata as ud
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,features
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from build import ROOT,FULL,OUT,FAMILIES,CORE,load,sha

PAPER='#faf9f5';INK='#171b1a';SUB='#656e68';RULE='#d8ddd6';ACCENT='#176952'
TEXT=[
'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
'abcdefghijklmnopqrstuvwxyz 0123456789',
'Build a brighter tomorrow. Quality & Rhythm.',
'Café, déjà vu, naïve — Straße & Æther.',
'Ďábel Ľudovít Ťažký Őrült Łódź Œuvre',
'Įvairūs žmonės ąęįų Ǫǫ Ǭǭ — ĄĘĮŲ',
'İstanbul ıslak  ſ ƒ ð þ ŋ ĸ',
'Tiếng Việt: Nguyễn, Trường, cộng hòa',
'ÀÁÂÃÄÅ ãăą éêěẽ ìíîï ủứựů ệặộở',
'The quick brown fox jumps over the lazy dog.',
'Sphinx of black quartz, judge my vow.',
'office affinity efficient fluffy — AVATAR To Wa',
]
SYMBOLS=[
'0123456789  0123456789',
'€ £ $ ¥ ₹ ₩ ₽ ₺ ₴ ₿ ¢ ¤ © ® ™',
'(ABC) [abc] {xyz} «…» “…” ‘…’ !? ¡¿',
'. , : ; / \\ - – — _ | # @ & * % ‰',
'¼ ½ ¾ ⅐ ⅓ ⅒ ⅞ ⅘ ⅔ ⅖ ⅗ ⅚',
'²³⁴⁵⁶⁷⁸⁹ ₀₁₂₃₄₅₆₇₈₉',
'Δ Π Σ Ω μ π ∂ ∆ ∏ ∑ ∫ √ ∞ ∅',
'+ − ± × ÷ = ≠ ≈ < > ≤ ≥ ∧ ∨',
'← ↑ → ↓ ↔ ↕ ↖ ↗ ↘ ↙ ↵',
'⇐ ⇑ ⇒ ⇓ ⇔ ⇕  ⌘ ⌥ ⎋ ✓',
'■ □ ● ○ § ¶ † ‡ •',
'Ąą Ęę Įį Ųų Ǫǫ Ǭǭ  Ďď Ľľ Ťť',
]
FEATURE_ROWS=[
('ss01 / alternative a','a á à ä ą', ['ss01']),
('ss02 / alternative g','g ĝ ğ ġ ģ', ['ss02']),
('ss03 / y and tittles','y ý ÿ i j í ì î ï', ['ss03']),
('ss04 / sweeping R','R Ŕ Ŗ Ř', ['ss04']),
('ss05 / clarity I and l','Il1 Ill Illicit', ['ss05']),
('liga / standard ligatures','office affinity fluffy', ['liga']),
('dlig / discretionary ligatures','st ct instant strict', ['dlig']),
('zero + tnum / tabular slashed figures','0123456789 001188', ['zero','tnum']),
('frac / fraction shaping','12/34 1/2 345/678', ['frac']),
('sups / superscript figures','0123456789', ['sups']),
('subs / subscript figures','0123456789', ['subs']),
('mark + mkmk / real combining marks','x\u0301\u0301 x\u0323\u0323 A\u0328 e\u0328 O\u031B\u0301', ['mark','mkmk']),
]

def label(draw,xy,value,size=22,color=INK):draw.text(xy,value,font_size=size,fill=color)
def path_for(family):return OUT/'fonts'/f'{family}FullDraft-Reference.otf'
def face(family,size):return ImageFont.truetype(str(path_for(family)),size,layout_engine=ImageFont.Layout.RAQM)
def draw_line(draw,xy,text,font,width,settings=None):
    advance=draw.textlength(text,font=font,features=settings)
    if advance>width:raise ValueError('Proof line exceeds its allocated width: '+text)
    draw.text(xy,text,font=font,features=settings,fill=INK)

def sheet(output,family,rows,title):
    im=Image.new('RGB',(2200,1900),PAPER);d=ImageDraw.Draw(im)
    label(d,(64,40),family+' / '+title,30,ACCENT)
    label(d,(64,92),'REFERENCE CUT - actual compiled CFF / approved core retained / remaining drawings await final review',21,SUB)
    d.line((64,136,2136,136),fill=RULE,width=2)
    for index,row in enumerate(rows):
        size=82
        while ImageDraw.Draw(im).textlength(row,font=face(family,size))>2072:size-=1
        draw_line(d,(64,175+index*138),row,face(family,size),2072)
    target=output/f'{family}-{title.lower().replace(" ","-")}.png';im.save(target)
    return target

def main():
    if not features.check_feature('raqm'):raise SystemExit('RAQM shaping is required; never use basic unshaped proofs')
    build=json.loads((OUT/'build.json').read_text())
    if build['stage']!='full-reference-review':raise SystemExit('Full proofs require a full build')
    for p,v in build['source_inputs'].items():
        if sha(ROOT/p)!=v:raise ValueError('Stale build: '+p)
    output=FULL/'proofs';output.mkdir(parents=True,exist_ok=True)
    allpaths=[];data={};atlas_manifest=[]
    im=Image.new('RGB',(2200,1540),PAPER);d=ImageDraw.Draw(im)
    label(d,(65,38),'LIHUIT / ZAYJU  -  FULL REFERENCE',30,ACCENT)
    label(d,(65,91),'The approved core, extended to the complete existing repertoire.',30)
    for i,family in enumerate(FAMILIES):
        y=175+i*650;label(d,(65,y),family,42)
        label(d,(410,y+12),'810 CODEPOINTS / 986 GLYPHS / ONE REFERENCE CUT',20,SUB)
        font=face(family,150);draw_line(d,(55,y+75),'Build a brighter tomorrow.',font,2090)
        draw_line(d,(65,y+291),'ABCDEFGHIJKLMNOPQRSTUVWXYZ',face(family,75),2090)
        draw_line(d,(65,y+399),'abcdefghijklmnopqrstuvwxyz 0123456789',face(family,75),2090)
        draw_line(d,(65,y+505),'Café  Straße  Ľudovít  Őrült  Nguyễn  ąęįų',face(family,64),2090)
        if i==0:d.line((65,y+630,2135,y+630),fill=RULE,width=2)
    label(d,(65,1483),'No extra weights, installation, merge, release or deployment is implied by this reference-cut proof.',21,SUB)
    im.save(output/'overview.png');allpaths.append(output/'overview.png')
    for family in FAMILIES:
        source=load(family);cmap={cp:g.name for g in source for cp in g.unicodes}
        for sample in TEXT+SYMBOLS+[r[1] for r in FEATURE_ROWS]:
            missing=set(map(ord,sample))-set(cmap)
            if missing:raise ValueError(('Unsupported proof text would fallback',sample,[hex(cp) for cp in missing]))
        allpaths.extend([sheet(output,family,TEXT,'Text and languages'),sheet(output,family,SYMBOLS,'Symbols and marks')])
        im=Image.new('RGB',(2400,1980),PAPER);d=ImageDraw.Draw(im)
        label(d,(65,38),family+' / OPENTYPE FEATURES',31,ACCENT)
        label(d,(65,91),'Left: defaults (liga off for comparison). Right: the named feature enabled. Actual CFF rendering.',23,SUB)
        for i,(title,sample,settings) in enumerate(FEATURE_ROWS):
            y=160+i*149;label(d,(65,y),title,20,SUB)
            f=face(family,70)
            while max(d.textlength(sample,font=f,features=['-liga','-dlig']),d.textlength(sample,font=f,features=settings))>1095:f=face(family,f.size-1)
            draw_line(d,(65,y+28),sample,f,1095,['-liga','-dlig'])
            draw_line(d,(1240,y+28),sample,f,1095,settings)
            d.line((65,y+136,2335,y+136),fill=RULE,width=1)
        p=output/f'{family}-features.png';im.save(p);allpaths.append(p)
        # Render every output glyph by its actual charstring through a throwaway
        # in-memory cmap. The user's font files and encoded coverage never change.
        with TTFont(path_for(family)) as f:
            names=f.getGlyphOrder();table=CmapSubtable.newSubtable(4);table.platformID=3;table.platEncID=1;table.language=0
            table.cmap={0xE000+i:n for i,n in enumerate(names)};f['cmap'].tables=[table]
            buf=io.BytesIO();f.save(buf);proof_font=ImageFont.truetype(io.BytesIO(buf.getvalue()),78)
            for page in range(math.ceil(len(names)/96)):
                im=Image.new('RGB',(2400,1560),PAPER);d=ImageDraw.Draw(im)
                label(d,(45,30),family+f' / ALL GLYPHS / {page+1:02d}',27,ACCENT)
                label(d,(45,74),'Actual CFF outlines by glyph name. Technical spaces remain blank; atlas mapping is temporary and not font coverage.',18,SUB)
                for slot,name in enumerate(names[page*96:(page+1)*96]):
                    index=page*96+slot;col=slot%12;row=slot//12;x=25+col*197;y=123+row*175
                    d.rectangle((x,y,x+189,y+165),outline=RULE,width=1)
                    label(d,(x+8,y+6),name,14,SUB)
                    codes=source[name].unicodes
                    label(d,(x+8,y+27),' '.join(f'{cp:04X}' for cp in codes)[:24] or 'feature / helper',12,SUB)
                    char=chr(0xE000+index);b=proof_font.getbbox(char,anchor='ls')
                    size=78;local=proof_font
                    while b[2]-b[0]>172:
                        size-=1;local=ImageFont.truetype(io.BytesIO(buf.getvalue()),size);b=local.getbbox(char,anchor='ls')
                    dx=x+94-(b[0]+b[2])/2;baseline=y+111
                    if b[3]>45:baseline=y+145-b[3]
                    d.text((dx,baseline),char,font=local,anchor='ls',fill=INK)
                target=output/'atlas'/f'{family}-{page+1:02d}.png';target.parent.mkdir(exist_ok=True);im.save(target);allpaths.append(target)
                atlas_manifest.append({'family':family,'page':page+1,'file':target.relative_to(output).as_posix(),'glyphs':names[page*96:(page+1)*96]})
        entries=[]
        for name in source.lib.get('public.glyphOrder',source.keys()):
            if name not in source:continue
            g=source[name];rec=DecomposingRecordingPen(source);g.draw(rec);pen=SVGPathPen(None);rec.replay(pen)
            approved=any(chr(cp) in CORE for cp in g.unicodes)
            entries.append({'name':name,'advance':g.width,'codes':[f'U+{cp:04X}' for cp in g.unicodes],
                            'chars':''.join(chr(cp) for cp in g.unicodes),'path':pen.getCommands(),
                            'approved_core':approved,'components':[c.baseGlyph for c in g.components],'note':g.note or ''})
        if len(entries)!=len(source):raise ValueError('Source review omits glyphs')
        data[family]=entries
    template=(FULL/'tools/review-template.html').read_text()
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    (output/'review.html').write_text(template.replace('__GLYPH_DATA__',encoded),encoding='utf-8')
    atlas_text=['# Complete reference glyph atlas','', 'Every entry is a render of the actual CFF glyph, including unencoded feature glyphs. The temporary atlas cmap is never saved as a font. Blank technical/control glyphs are intentional.','']
    for family in FAMILIES:
        atlas_text+=['## '+family,'']
        for row in atlas_manifest:
            if row['family']==family:atlas_text+=[f"### Page {row['page']}: {row['glyphs'][0]} — {row['glyphs'][-1]}",f"![{family} page {row['page']}]({row['file']})",'']
    (output/'atlas.md').write_text('\n'.join(atlas_text))
    meta={'scope':__doc__,'renderer':'Pillow/FreeType '+features.version_module('freetype2')+' with RAQM','source_inputs':build['source_inputs'],
          'font_inputs':[r for r in build['records'] if r['format']=='otf'],'atlas':atlas_manifest,
          'proofs':{p.relative_to(output).as_posix():sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='manifest.json'}}
    (output/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    print('Rendered',len(allpaths),'actual-font sheets; atlas covers',sum(len(r['glyphs']) for r in atlas_manifest),'glyphs. Offline source review contains both complete UFOs.')
if __name__=='__main__':main()
