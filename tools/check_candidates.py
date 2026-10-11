#!/usr/bin/env python3
"""Validate the 0.500 release: approved Regular bytes, plus stored-master styles.

Regular 400 upright must match a fresh compile of the hash-locked drawings,
including layout tables. Other styles must match their stored masters in
coverage, names and carets, and must not be compared as if they were Regular.
Forced decomposition covers every upright TTF plus Regular and Black Oblique.
Remaining Obliques get the same shaping assertions and a fixed review sample,
because they are 10° derivatives of masters that passed the full pair set.
"""
from __future__ import annotations
import io,json,subprocess,tempfile,unicodedata as ud
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from ufoLib2 import Font
import ots
from pathlib import Path
from release_support import (ROOT,DIST,WORK,FAMILIES,reference,reference_checks,read_build,version,sha,
    styles,ps_name,legacy_names,font_path,master_path,full_decomposition_targets)
checks=reference_checks()
REVIEW='BMRage23689'

def signature(font,name):
    gs=font.getGlyphSet();pen=DecomposingRecordingPen(gs);gs[name].draw(pen)
    return (font['hmtx'].metrics[name],pen.value)

def open_source(family,weight,oblique,cache):
    key=(family,weight,oblique)
    if key not in cache:
        if weight==400 and not oblique:cache[key]=reference.load(family)
        else:cache[key]=Font.open(master_path(family,weight,oblique))
    return cache[key]

def assert_identity(font,family,weight,oblique):
    legacy_family,legacy_style,typo_family,typo_style=legacy_names(family,weight,oblique)
    post=ps_name(family,weight,oblique)
    assert font['name'].getDebugName(1)==legacy_family
    assert font['name'].getDebugName(2)==legacy_style
    assert font['name'].getDebugName(16)==typo_family
    assert font['name'].getDebugName(17)==typo_style
    assert font['name'].getDebugName(6)==post and font['name'].getDebugName(9)=='zayju'
    assert font['name'].getDebugName(13)==(ROOT/'OFL.txt').read_text().strip()
    assert font['name'].getDebugName(0)==(ROOT/'OFL.txt').read_text().splitlines()[0]
    assert font['name'].getDebugName(11)=='https://github.com/SheathedSharp/oh-my-font'
    assert font['name'].getDebugName(5)=='Version '+version()
    assert 'Oblique' in typo_style if oblique else 'Italic' not in typo_style
    assert abs(font['head'].fontRevision-float(version()))<1/65536
    assert font['OS/2'].usWeightClass==weight and font['OS/2'].fsType==0 and 'fvar' not in font
    assert abs(font['post'].italicAngle-(-10 if oblique else 0))<0.01
    selection=font['OS/2'].fsSelection
    assert bool(selection&1)==oblique and bool(selection&(1<<9))==oblique
    assert bool(selection&(1<<5))==(weight==700)
    assert bool(selection&(1<<6))==(weight!=700 and not oblique)
    if oblique:
        assert font['hhea'].caretSlopeRise==1000 and font['hhea'].caretSlopeRun==176
    assert not any('Full Draft' in n.toUnicode() or 'Core Study' in n.toUnicode() for n in font['name'].names)
    if 'CFF ' in font:
        assert font['CFF '].cff.fontNames==[post] and font['CFF '].cff.topDictIndex[0].FamilyName==family
    assert font['STAT'].table.AxisValueCount==2

def oblique_sample(path):
    with TTFont(path) as font:
        shaper=checks.Shaper(font);cmap=font.getBestCmap()
        for char in REVIEW:
            result=shaper.shape(char)
            assert result and all(row['glyph']!='.notdef' for row in result),(path.name,char)
        pre=shaper.shape('é');decomposed=shaper.shape('e\u0301')
        assert pre and decomposed and pre[0]['glyph']!='.notdef'
        assert abs(pre[0]['advance']-sum(row['advance'] for row in decomposed))<=1
        assert 0x00E9 in cmap and 0x0301 in cmap
    return {'review_glyphs':REVIEW,'e_acute_shaped':True,'scope':'fixed sample; full forced decomposition ran on this weight’s upright master'}

def main():
    report=read_build();WORK.mkdir(exist_ok=True);target=json.loads((ROOT/'design/full-01/repertoire.json').read_text())
    source_records=[];approved={}
    for family in FAMILIES:
        u,result=checks.source_check(family,target);approved[family]=u;source_records.append(result)
        print(f'{family}: {len(u)} accepted Regular glyphs, mark clearance and core lock passed',flush=True)
    results=[];forced=[];samples=[];sources={}
    full={row[3] for row in full_decomposition_targets()}
    sanitizer=Path(ots.__file__).with_name('ots-sanitize')
    with tempfile.TemporaryDirectory(prefix='release-ots-',dir=WORK) as temp:
        for i,row in enumerate(report['records']):
            path=DIST/row['file'];proc=subprocess.run([str(sanitizer),str(path),str(Path(temp)/f'{i}.sfnt')],capture_output=True,text=True)
            if proc.returncode:raise ValueError((row['file'],'OTS',proc.stdout,proc.stderr))
            family,weight,oblique=row['family'],row['weight'],row['oblique']
            with TTFont(path,checkChecksums=2) as f:
                cmap=f.getBestCmap();gs=f.getGlyphSet()
                assert len(gs)==986 and len(cmap)==810 and set(cmap)==set(map(int,target['cmap']))
                assert_identity(f,family,weight,oblique)
                features={r.FeatureTag for tag in ('GSUB','GPOS') for r in f[tag].table.FeatureList.FeatureRecord}
                assert features>=checks.FEATURES
                cache_key=(family,row['format']=='otf')
                if cache_key not in approved:
                    approved[cache_key]=reference.compile_font(approved[family],cache_key[1])
                buffer=io.BytesIO();approved[cache_key].save(buffer);buffer.seek(0)
                with TTFont(buffer) as base:
                    assert f.getGlyphOrder()==base.getGlyphOrder()
                    assert f.getBestCmap()==base.getBestCmap()
                    if weight==400 and not oblique:
                        for tag in ('cmap','hmtx','GDEF','GSUB','GPOS'):
                            assert f.getTableData(tag)==base.getTableData(tag),(path.name,tag,'approved layout changed')
                        for name in f.getGlyphOrder():
                            assert signature(f,name)==signature(base,name),(path.name,name,'approved glyph changed')
                for name in f.getGlyphOrder():
                    result=checks.inspect(gs[name],gs);assert result['valid'],(path.name,name,'invalid serialized contour')
                shaper=checks.Shaper(f);layout=checks.assert_shapes(shaper);encoded=canonical=0
                for cp in cmap:
                    if cp not in checks.SPACES:
                        shaped=shaper.shape(chr(cp));assert shaped and all(r['glyph']!='.notdef' for r in shaped);encoded+=1
                    nfd=ud.normalize('NFD',chr(cp))
                    if len(nfd)>1 and all(ord(c) in cmap for c in nfd):
                        assert shaper.shape(chr(cp))==shaper.shape(nfd);canonical+=1
                source=open_source(family,weight,oblique,sources)
                caret=f['GDEF'].table.LigCaretList;assert len(caret.Coverage.glyphs)==7
                for name,g in zip(caret.Coverage.glyphs,caret.LigGlyph):
                    assert [c.Coordinate for c in g.CaretValue]==source.lib['de.zayju.ligatureCarets'][name]
            row_result={**row,'ots_exit':0,'serialized_glyphs_checked':986,'approved_glyphs_and_layout_identical':weight==400 and not oblique,
                        'layout_regressions':layout,'encoded_checks':encoded,'canonical_pairs':canonical,'ligature_carets':7}
            results.append(row_result)
            if row['format']=='ttf' and row['file'] in full:
                result=checks.forced_decomposition_check(path);forced.append({'file':row['file'],'sha256':row['sha256'],**result})
                print(row['file'],'OTS/986 glyphs and',result['pairs_checked'],'forced-feature combinations passed',flush=True)
            elif row['format']=='ttf' and oblique:
                sample=oblique_sample(path);samples.append({'file':row['file'],'sha256':row['sha256'],**sample})
                print(row['file'],'OTS/986 glyphs and oblique review sample passed',flush=True)
            else:
                print(row['file'],'OTS/986 glyphs passed',flush=True)
    conversion=[]
    for family in FAMILIES:
        for row in styles():
            stem=ps_name(family,row['weight'],row['oblique'])
            with TTFont(DIST/'ttf'/family/f'{stem}.ttf') as a,TTFont(DIST/'otf'/family/f'{stem}.otf') as b,TTFont(DIST/'woff2'/family/f'{stem}.woff2') as w:
                assert a['hmtx'].metrics==w['hmtx'].metrics and a.getBestCmap()==w.getBestCmap();ga=a.getGlyphSet();gb=b.getGlyphSet();distances=[]
                for name in a.getGlyphOrder():
                    assert a['glyf'][name].getCoordinates(a['glyf'])==w['glyf'][name].getCoordinates(w['glyf'])
                    x=checks.inspect(ga[name],ga)['geometry'];y=checks.inspect(gb[name],gb)['geometry']
                    distance=0 if x.is_empty and y.is_empty else x.boundary.segmentize(2).hausdorff_distance(y.boundary.segmentize(2))
                    assert distance<=1.6,(family,stem,name,distance)
                    distances.append(distance)
                conversion.append({'family':family,'style':row['style'],'glyphs':986,'woff2_lossless':True,'max_sampled_distance_upm':round(max(distances),6),'sampled_gate_upm':1.6})
            print(family,row['style'],'TTF/OTF/WOFF2 within 1.6 UPM',flush=True)
    expected_full={item[3] for item in full_decomposition_targets()}
    assert {row['file'] for row in forced}==expected_full
    assert all(not row['failures'] and row['pairs_checked']==2964 for row in forced)
    result={'version':version(),'scope':'32 styles (8 weights × upright/Oblique × 2 families). Regular 400 upright matches the approved drawings. Other styles are stored masters. Oblique is a 10° slant, not a drawn Italic. Latin-limited; Sigma finding retained.',
            'source_inputs_sha256':report['source_inputs_sha256'],'source':source_records,'records':results,
            'forced_decomposition':forced,'oblique_samples':samples,'conversion':conversion,
            'forced_decomposition_policy':'full pair set on 20 TTF files (every upright, plus Regular and Black Oblique per family); remaining Oblique TTFs use a fixed review sample','passed':True}
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    assert '/Users/' not in text and '/home/' not in text
    (WORK/'candidate-checks.json').write_text(text);print('PASS: 96 candidates. Regular 400 matches approved drawings; other styles checked as stored masters.')
if __name__=='__main__':main()
