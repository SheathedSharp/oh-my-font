#!/usr/bin/env python3
"""Export/import one weight's glyph as an editable SVG without touching others.

Imports intentionally accept just one path and the exported y-axis flip. Flatten
any other editor transforms before importing. Metadata/advance/anchors remain
unchanged. Related accented forms are separate drawings and require explicit
review; this tool never silently regenerates them from historical scaffolds.
"""
import argparse,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from masters import Designer,MASTER_ROOT,Outline,WEIGHTS
from outline_qa import inspect

def write_master(path,data):
    glyphs=data.pop('glyphs')
    text=json.dumps(data,ensure_ascii=False,indent=2)[:-2]+',\n  "glyphs": [\n'+',\n'.join('    '+json.dumps(g,ensure_ascii=False,separators=(',',':')) for g in glyphs)+'\n  ]\n}\n'
    temp=path.with_suffix('.json.tmp')
    try:
        temp.write_text(text,encoding='utf-8');temp.replace(path)
    finally:
        if temp.exists():temp.unlink()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['export','import'])
    p.add_argument('--family',required=True,choices=['LihuiT','zayJu'])
    p.add_argument('--weight',required=True,type=int,choices=list(WEIGHTS))
    p.add_argument('--glyph',required=True)
    p.add_argument('--svg',required=True,type=Path)
    p.add_argument('--source-root',type=Path,default=MASTER_ROOT,help='Master directory; useful for isolated drawing drafts')
    a=p.parse_args();d=Designer(a.family,a.weight,source_root=a.source_root)
    if a.glyph not in d.glyphs:raise SystemExit('Unknown glyph name')
    path=d.source_path;data=json.loads(path.read_text());entry=next(g for g in data['glyphs'] if g['name']==a.glyph)
    if a.operation=='export':
        if a.svg.exists():raise SystemExit('Refusing to overwrite existing SVG')
        x0,y0,x1,y1=d.glyphs[a.glyph].geometry.bounds
        text=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0-40} {-y1-40} {max(1,x1-x0)+80} {max(1,y1-y0)+80}">\n<title>{escape(a.family)} {a.weight}: {escape(a.glyph)}</title>\n<g transform="scale(1,-1)"><path d="{escape(entry["path"])}"/></g>\n</svg>\n'
        a.svg.write_text(text,encoding='utf-8');print('Exported',a.svg);return
    root=ET.fromstring(a.svg.read_text(encoding='utf-8'))
    paths=[e for e in root.iter() if e.tag.rsplit('}',1)[-1]=='path']
    if len(paths)!=1:raise SystemExit('Expected exactly one path')
    for element in root.iter():
        transform=element.get('transform')
        if transform is not None and (element.tag.rsplit('}',1)[-1]!='g' or transform!='scale(1,-1)'):
            raise SystemExit('Flatten editor transforms before import; only the exported y flip is accepted')
        if element.tag.rsplit('}',1)[-1] not in ('svg','g','path','title','desc','metadata'):
            raise SystemExit('Unsupported SVG element; export only the glyph path')
    new_path=paths[0].get('d','');result=inspect(Outline(new_path))
    if not result['valid']:raise SystemExit('Invalid or degenerate outline; master was not changed')
    if d.glyphs[a.glyph].geometry.is_empty != (result['geometry'].is_empty):
        raise SystemExit('Refusing to accidentally add/remove the entire glyph')
    entry['path']=new_path
    write_master(path,data)
    print(f'Updated only {a.family}/{a.weight}: {a.glyph}. Review related accented/alternate glyphs and run the full outline gate.')
if __name__=='__main__':main()
