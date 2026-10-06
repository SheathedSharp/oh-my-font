#!/usr/bin/env python3
"""Validate the exact official release, including every approved glyph and layout.

Reuses the approved reference's substantive source/mark/feature gates, but checks
new official filenames and metadata. All rendered geometry and layout tables are
also compared to a fresh accepted-source compile, not just screenshots or counts.
"""
from __future__ import annotations
import io,json,subprocess,tempfile,unicodedata as ud
from functools import lru_cache
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
import ots
from pathlib import Path
from release_support import ROOT,DIST,WORK,FAMILIES,reference,reference_checks,read_build,version,sha
checks=reference_checks()

def signature(font,name):
    gs=font.getGlyphSet();pen=DecomposingRecordingPen(gs);gs[name].draw(pen)
    return (font['hmtx'].metrics[name],pen.value)

def main():
    report=read_build();WORK.mkdir(exist_ok=True);target=json.loads((ROOT/'design/full-01/repertoire.json').read_text())
    source_records=[];sources={}
    for family in FAMILIES:
        u,result=checks.source_check(family,target);sources[family]=u;source_records.append(result)
        print(f'{family}: {len(u)} accepted-source glyphs, mark clearance and core lock passed',flush=True)
    results=[];forced=[]
    sanitizer=Path(ots.__file__).with_name('ots-sanitize')
    with tempfile.TemporaryDirectory(prefix='release-ots-',dir=WORK) as temp:
        for i,row in enumerate(report['records']):
            path=DIST/row['file'];proc=subprocess.run([str(sanitizer),str(path),str(Path(temp)/f'{i}.sfnt')],capture_output=True,text=True)
            if proc.returncode:raise ValueError((row['file'],'OTS',proc.stdout,proc.stderr))
            baseline=reference.compile_font(sources[row['family']],row['format']=='otf')
            buffer=io.BytesIO();baseline.save(buffer);buffer.seek(0)
            with TTFont(path,checkChecksums=2) as f,TTFont(buffer) as approved:
                family=row['family'];post=family+'-Regular';cmap=f.getBestCmap();gs=f.getGlyphSet()
                assert len(gs)==986 and len(cmap)==810 and set(cmap)==set(map(int,target['cmap']))
                assert f['name'].getDebugName(1)==f['name'].getDebugName(16)==family
                assert f['name'].getDebugName(2)==f['name'].getDebugName(17)=='Regular'
                assert f['name'].getDebugName(6)==post and f['name'].getDebugName(9)=='zayju'
                assert f['name'].getDebugName(13)==(ROOT/'OFL.txt').read_text().strip()
                assert f['name'].getDebugName(0)==(ROOT/'OFL.txt').read_text().splitlines()[0]
                assert f['name'].getDebugName(11)=='https://github.com/SheathedSharp/oh-my-font'
                assert f['name'].getDebugName(5)=='Version '+version()
                assert abs(f['head'].fontRevision-float(version()))<1/65536
                assert f['OS/2'].usWeightClass==400 and f['post'].italicAngle==0 and f['OS/2'].fsType==0 and 'fvar' not in f
                assert not any('Full Draft' in n.toUnicode() or 'Core Study' in n.toUnicode() for n in f['name'].names)
                if 'CFF ' in f:
                    assert f['CFF '].cff.fontNames==[post] and f['CFF '].cff.topDictIndex[0].FamilyName==family
                features={r.FeatureTag for tag in ('GSUB','GPOS') for r in f[tag].table.FeatureList.FeatureRecord}
                assert features>=checks.FEATURES
                # Names/version may differ; every accepted outline, advance and
                # shaping table must survive official promotion exactly.
                assert f.getGlyphOrder()==approved.getGlyphOrder()
                for tag in ('cmap','hmtx','GDEF','GSUB','GPOS'):
                    assert f.getTableData(tag)==approved.getTableData(tag),(path.name,tag,'layout changed')
                for name in f.getGlyphOrder():
                    assert signature(f,name)==signature(approved,name),(path.name,name,'approved glyph changed')
                    r=checks.inspect(gs[name],gs);assert r['valid'],(path.name,name,'invalid serialized contour')
                shaper=checks.Shaper(f);layout=checks.assert_shapes(shaper);encoded=canonical=0
                for cp in cmap:
                    if cp not in checks.SPACES:
                        result=shaper.shape(chr(cp));assert result and all(r['glyph']!='.notdef' for r in result);encoded+=1
                    nfd=ud.normalize('NFD',chr(cp))
                    if len(nfd)>1 and all(ord(c) in cmap for c in nfd):
                        assert shaper.shape(chr(cp))==shaper.shape(nfd);canonical+=1
                caret=f['GDEF'].table.LigCaretList;assert len(caret.Coverage.glyphs)==7
                for name,g in zip(caret.Coverage.glyphs,caret.LigGlyph):assert [c.Coordinate for c in g.CaretValue]==sources[family].lib['de.zayju.ligatureCarets'][name]
            results.append({**row,'ots_exit':0,'serialized_glyphs_checked':986,'approved_glyphs_and_layout_identical':True,
                            'layout_regressions':layout,'encoded_checks':encoded,'canonical_pairs':canonical,'ligature_carets':7})
            result=checks.forced_decomposition_check(path);forced.append({'file':row['file'],'sha256':row['sha256'],**result})
            print(row['file'],'metadata/OTS/986 accepted glyphs and',result['pairs_checked'],'forced-feature combinations passed',flush=True)
    conversion=[]
    for family in FAMILIES:
        with TTFont(DIST/'ttf'/family/f'{family}-Regular.ttf') as a,TTFont(DIST/'otf'/family/f'{family}-Regular.otf') as b,TTFont(DIST/'woff2'/family/f'{family}-Regular.woff2') as w:
            assert a['hmtx'].metrics==w['hmtx'].metrics and a.getBestCmap()==w.getBestCmap();ga=a.getGlyphSet();gb=b.getGlyphSet();distances=[]
            for name in a.getGlyphOrder():
                assert a['glyf'][name].getCoordinates(a['glyf'])==w['glyf'][name].getCoordinates(w['glyf'])
                x=checks.inspect(ga[name],ga)['geometry'];y=checks.inspect(gb[name],gb)['geometry']
                distance=0 if x.is_empty and y.is_empty else x.boundary.segmentize(2).hausdorff_distance(y.boundary.segmentize(2))
                assert distance<=1.6,(family,name,distance)
                distances.append({'glyph':name,'sampled_distance_upm':round(distance,6)})
            conversion.append({'family':family,'glyphs':986,'woff2_lossless':True,'max':max(distances,key=lambda x:x['sampled_distance_upm']),'sampled_gate_upm':1.6})
    result={'version':version(),'scope':'two approved Regular faces; no unapproved weights; no full-platform or complete-Unicode claim',
            'source_inputs_sha256':report['source_inputs_sha256'],'source':source_records,'records':results,'forced_decomposition':forced,'conversion':conversion,'passed':True}
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    assert '/Users/' not in text and '/home/' not in text
    (WORK/'candidate-checks.json').write_text(text);print('PASS: all 6 official candidates, all glyphs and layout equal to approved drawings.')
if __name__=='__main__':main()
