#!/usr/bin/env python3
"""Render actual compiled files for optical review; never simulate CSS weights."""
import argparse,hashlib,json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,features
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from masters import WEIGHTS
VERSION=(ROOT/'VERSION').read_text().strip()

def font_path(root,family,weight,oblique=False,fmt='ttf'):
    name=('Oblique' if weight==400 else WEIGHTS[weight]+'Oblique') if oblique else WEIGHTS[weight]
    return root/fmt/family/f'{family}-{name}.{fmt}'

def label(draw,xy,text,size=24):draw.text(xy,text,fill='black',font_size=size)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'docs/qa'/VERSION);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    records=[];samples=('abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789','ÀÁÂÃÄÅ Ç ÉÈÊË Ñ ÖÜ ß  fi ffi  1/3 0OIl  Őő Űű')
    for family in ('LihuiT','zayJu'):
      for oblique in (False,True):
        im=Image.new('RGB',(2200,2220),'white');draw=ImageDraw.Draw(im)
        label(draw,(34,25),f'{family} / {"Oblique" if oblique else "Upright"} / actual {VERSION} TTF outlines',32)
        for i,weight in enumerate(WEIGHTS):
            path=font_path(ROOT/'dist',family,weight,oblique);font=ImageFont.truetype(str(path),60)
            y=105+i*260;label(draw,(34,y+12),str(weight),30)
            for j,text in enumerate(samples):draw.text((170,y+j*76),text,font=font,fill='black')
            records.append({'file':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sample_pixels':60})
        target=a.output/f'{family}-{"oblique" if oblique else "upright"}-all-weights.png';im.save(target)
      if a.baseline:
        im=Image.new('RGB',(2200,1550),'white');draw=ImageDraw.Draw(im)
        label(draw,(34,25),f'{family} / light junctions / baseline and actual rebuilt files',32)
        for i,weight in enumerate((100,300,400)):
            for j,(root,fmt,title) in enumerate(((a.baseline,'ttf','0.301 TTF'),(ROOT/'dist','ttf',VERSION+' TTF'),(ROOT/'dist','otf',VERSION+' CFF'))):
                y=100+i*470+j*145;path=font_path(root,family,weight,False,fmt)
                label(draw,(30,y+32),f'{weight} / {title}',24)
                font=ImageFont.truetype(str(path),130)
                draw.text((280,y),'abdeghmnpry BDR 23689',font=font,fill='black')
                if root==a.baseline:records.append({'baseline_file':path.relative_to(a.baseline).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
                else:records.append({'comparison_file':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sample_pixels':130})
        im.save(a.output/f'{family}-light-before-after.png')
    if a.baseline:
        im=Image.new('RGB',(2200,1350),'white');draw=ImageDraw.Draw(im)
        label(draw,(32,25),'zayJu 900 / separate double-acute strokes / actual exports',30)
        for i,oblique in enumerate((False,True)):
            for j,(root,fmt,title) in enumerate(((a.baseline,'ttf','0.301 TTF'),(ROOT/'dist','ttf',VERSION+' TTF'),(ROOT/'dist','otf',VERSION+' CFF'))):
                path=font_path(root,'zayJu',900,oblique,fmt);font=ImageFont.truetype(str(path),165)
                y=105+i*600+j*190;label(draw,(32,y+40),('Oblique' if oblique else 'Upright')+' / '+title,22)
                draw.text((350,y),'Őő Űű  ˝  O\u030B U\u030B',font=font,fill='black')
                key='baseline_file' if root==a.baseline else 'comparison_file'
                records.append({key:path.relative_to(root if root==a.baseline else ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sample_pixels':165})
        im.save(a.output/'zayJu-900-doubleacute-before-after.png')
    (a.output/'proof-manifest.json').write_text(json.dumps({'renderer':'Pillow / FreeType '+features.version_module('freetype2'),'scope':'32-style alphabet/number/language specimens; six light-cut comparisons; not a claim of manual approval for every glyph','files':records},indent=2)+'\n')
    print('Rendered all 32 styles and',6 if a.baseline else 0,'baseline/TTF/CFF light-cut comparisons')
if __name__=='__main__':main()
