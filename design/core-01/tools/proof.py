#!/usr/bin/env python3
"""Create honest actual-font raster proofs and a self-contained curve review page.

PNGs are rendered from the compiled CFF files. The interactive HTML explicitly
shows the authoritative UFO curves (not a fallback font) and contains no font
binary. Only the supported core repertoire can be typeset in that page.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,features
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.recordingPen import RecordingPen
from build import STUDY,ROOT,CORE,FAMILIES,load_source

INK='#171b1a';PAPER='#faf9f5';MUTED='#626a67';LINE='#dbded8';ACCENT='#166854'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def label(draw,xy,text,size=25,fill=INK):draw.text(xy,text,fill=fill,font_size=size)
def face(folder,family,size,fmt='otf'):
    return ImageFont.truetype(str(folder/'fonts'/(family+'CoreStudy01-Reference.'+fmt)),size)
def text(draw,xy,value,font):draw.text(xy,value,font=font,fill=INK)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=ROOT/'.release-work/core-01')
    p.add_argument('--output',type=Path,default=STUDY/'proofs')
    p.add_argument('--baseline',type=Path,help='Explicit rejected-PR build directory, only for comparison; never a drawing source')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    if not a.baseline and (a.output/'before-after.png').exists():
        raise SystemExit('Existing comparison proof: pass --baseline to regenerate it, or use a new --output directory. Refusing to relabel a stale comparison.')
    manifest={'renderer':'Pillow/FreeType '+features.version_module('freetype2'),'font_inputs':[],'images':[]}
    im=Image.new('RGB',(2000,1600),PAPER);d=ImageDraw.Draw(im)
    label(d,(76,43),'CORE 01',31,ACCENT);label(d,(76,91),'A new curve language, before the rest of the alphabet.',32)
    label(d,(1448,53),'11 GLYPHS / FAMILY',22,MUTED);label(d,(1448,86),'REFERENCE CUT / NOT APPROVED',18,MUTED)
    for i,family in enumerate(FAMILIES):
        y=175+i*695
        d.line((76,y,1924,y),fill=LINE,width=2)
        label(d,(76,y+31),family,37)
        label(d,(400,y+40),'WARM / HUMANIST' if family=='LihuiT' else 'FLUID / EXPRESSIVE',21,ACCENT)
        label(d,(1500,y+40),'Newly drawn cubic outlines',18,MUTED)
        text(d,(56,y+75),'BMR age',face(a.build,family,255))
        text(d,(1250,y+100),'23689',face(a.build,family,198))
        text(d,(66,y+386),'Rage  Mega',face(a.build,family,195))
        label(d,(1420,y+466),'Real font export.',22,MUTED)
        label(d,(1420,y+501),'No synthetic weight.',22,MUTED)
        label(d,(1420,y+536),'No missing-letter fallback.',22,MUTED)
        path=a.build/'fonts'/(family+'CoreStudy01-Reference.otf')
        manifest['font_inputs'].append({'file':path.relative_to(a.build).as_posix(),'sha256':sha(path),'family':family})
    label(d,(76,1540),'B M R a g e 2 3 6 8 9   /   Other characters and weights await your direction.',23,MUTED)
    overview=a.output/'overview.png';im.save(overview);manifest['images'].append(overview.name)

    # Large B/M/R views reveal the waist, shoulders and leg without decorative effects.
    im=Image.new('RGB',(2100,1240),PAPER);d=ImageDraw.Draw(im)
    label(d,(64,35),'B / M / R  -  SHAPE REVIEW',30,ACCENT)
    label(d,(64,84),'New individual curves, not the rejected box-and-stroke construction.',23,MUTED)
    for i,family in enumerate(FAMILIES):
        y=148+i*522;label(d,(65,y),family,32)
        new=face(a.build,family,450)
        for x,c in zip((255,820,1475),'BMR'):
            text(d,(x,y+8),c,new)
        label(d,(65,y+85),'CORE 01',20,MUTED)
    capitals=a.output/'capitals.png';im.save(capitals);manifest['images'].append(capitals.name)

    # Same UPM and pixel size for the rejected previous study and the new draft.
    if a.baseline:
        im=Image.new('RGB',(2000,1400),PAPER);d=ImageDraw.Draw(im)
        label(d,(65,36),'REJECTED PR #8  /  NEW CORE 01',29,ACCENT)
        label(d,(65,84),'Same pixel size. Previous fonts are a comparison only, never construction inputs.',23,MUTED)
        for i,family in enumerate(FAMILIES):
            y=155+i*594;label(d,(65,y),family,34)
            oldpath=a.baseline/'otf'/family/(family+'-Regular.otf')
            old=ImageFont.truetype(str(oldpath),190);new=face(a.build,family,190)
            label(d,(65,y+92),'PR #8',22,MUTED);text(d,(255,y+34),'BMR age 238',old)
            label(d,(65,y+325),'CORE 01',22,ACCENT);text(d,(255,y+266),'BMR age 238',new)
            manifest['font_inputs'].append({'baseline_file':oldpath.relative_to(a.baseline).as_posix(),'sha256':sha(oldpath),'baseline':'rejected PR #8, 3e0c54a'})
        path=a.output/'before-after.png';im.save(path);manifest['images'].append(path.name)

    # UFO-derived control-point SVGs and JSON; no recipe is retained to regenerate
    # a letter. Editable GLIF records stay authoritative.
    records={}
    for family in FAMILIES:
        u,cmap=load_source(family);entry={'paths':{},'kerning':{'/'.join(k):v for k,v in u.kerning.items()}}
        for c in CORE+' ':
            g=u[cmap[ord(c)]];pen=SVGPathPen(None);g.draw(pen);r=RecordingPen();g.draw(r)
            controls=[];nodes=[];current=None;start=None
            for op,pts in r.value:
                if op=='moveTo':current=start=pts[0];nodes.append(current)
                elif op=='lineTo':current=pts[0];nodes.append(current)
                elif op=='curveTo':
                    controls.extend(((current,pts[0]),(pts[2],pts[1])));nodes.append(pts[2]);current=pts[2]
                elif op=='closePath':current=start
            entry['paths'][c]={'name':g.name,'advance':g.width,'d':pen.getCommands(),'note':g.note or '',
                               'handles':controls,'nodes':nodes}
            if c==' ':continue
            svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -800 {g.width} 1080"><title>{family} Core 01: {c}</title><g transform="scale(1,-1)"><path d="{pen.getCommands()}" fill="black"/></g></svg>\n'
            target=a.output/'svg'/family/(g.name+'.svg');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(svg)
        records[family]=entry
    template=(STUDY/'tools/review-template.html').read_text()
    encoded=json.dumps(records,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    (a.output/'review.html').write_text(template.replace('__GLYPH_DATA__',encoded),encoding='utf-8')
    manifest['curve_source']='authoritative UFO3 GLIF records; HTML displays vectors, PNGs display real compiled CFF'
    manifest['sources']={p.relative_to(ROOT).as_posix():sha(p) for p in sorted((STUDY/'sources').rglob('*')) if p.is_file()}
    manifest['proof_files']={p.relative_to(a.output).as_posix():sha(p) for p in sorted(a.output.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Wrote actual-font proofs, 22 curve SVGs and self-contained review.html')
if __name__=='__main__':main()
