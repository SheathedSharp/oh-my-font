#!/usr/bin/env python3
"""Build ONLY the owner-approved Regular redesigns; never old or synthetic weights.

The approved UFOs remain unchanged. Compilation uses the accepted full-reference
compiler; promotion changes release identity/version metadata, not drawings or
OpenType layout. Outputs are never installed or published by this command.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'tools'))
from release_support import ROOT,DIST,FAMILIES,FORMATS,reference,validate_approval,source_hashes,expected_files,version,sha
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen

def geometry_signature(font,name):
    glyphs=font.getGlyphSet();pen=DecomposingRecordingPen(glyphs);glyphs[name].draw(pen)
    return (font['hmtx'].metrics[name],pen.value)

def promote(font,family):
    if family not in FAMILIES:raise ValueError('Unknown approved family')
    # Assert identity promotion does not alter any outline, width or layout table.
    before={n:geometry_signature(font,n) for n in font.getGlyphOrder()}
    layout={t:font.getTableData(t) for t in ('cmap','GDEF','GSUB','GPOS','hmtx')}
    ver=version();post=family+'-Regular'
    values={1:family,2:'Regular',3:f'{ver};zayj;{post}',4:family+' Regular',5:'Version '+ver,6:post,16:family,17:'Regular',
            10:'Approved redesigned Regular 400. 810 codepoints, 986 glyphs. No additional weights or italics are included.',
            11:'https://github.com/SheathedSharp/oh-my-font',9:'zayju',12:'https://github.com/SheathedSharp',
            0:(ROOT/'OFL.txt').read_text().splitlines()[0],13:(ROOT/'OFL.txt').read_text().strip(),14:'https://openfontlicense.org'}
    for name_id,text in values.items():
        font['name'].removeNames(nameID=name_id)
        font['name'].setName(text,name_id,3,1,0x409)
        try:font['name'].setName(text,name_id,1,0,0)
        except UnicodeEncodeError:pass
    font['head'].fontRevision=float(ver);font.recalcTimestamp=False
    if 'CFF ' in font:
        cff=font['CFF '].cff;cff.fontNames=[post];top=cff.topDictIndex[0]
        top.FullName=family+' Regular';top.FamilyName=family;top.Weight='Regular';top.version=ver
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
        u=reference.load(family)
        for fmt in FORMATS:
            font=promote(reference.compile_font(u,fmt=='otf'),family);font.flavor='woff2' if fmt=='woff2' else None
            path=dest/fmt/family/f'{family}-Regular.{fmt}';path.parent.mkdir(parents=True,exist_ok=True)
            if path.is_symlink():raise ValueError('Refusing output symlink')
            font.save(path)
            with TTFont(path,checkChecksums=2) as checked:
                if len(checked.getGlyphOrder())!=986 or len(checked.getBestCmap())!=810:raise ValueError('Incomplete approved candidate')
                for tag in checked.keys():
                    if tag!='GlyphOrder':checked.getTableData(tag)
                features=sorted({rec.FeatureTag for tag in ('GSUB','GPOS') for rec in checked[tag].table.FeatureList.FeatureRecord})
            records.append({'file':path.relative_to(dest).as_posix(),'family':family,'style':'Regular','weight':400,'format':fmt,
                            'glyphs':986,'codepoints':810,'bytes':path.stat().st_size,'features':features,'sha256':sha(path),'structural_check':'passed'})
            print('Built',path.relative_to(dest),flush=True)
    report={'project':'LihuiT / zayJu','version':version(),'scope':'approved-regular-only','files':6,'faces':2,
            'approved_commit':'4640e2b38bc20b72e4f5584113208fa819b5adc9','source_inputs_sha256':source_hashes(),
            'metadata_promotion_preserves_all_outlines_metrics_and_layout':True,'records':records,'seconds':round(time.monotonic()-started,3)}
    (dest/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Complete: 2 approved Regular faces / 6 files. No installation or publication.')
if __name__=='__main__':main()
