#!/usr/bin/env python3
"""Validate every new reference glyph, approved-core lock, marks and real font exports.

Coverage and rendering checks are not a claim of final visual approval. Distances
are sampled geometry checks; semantic combinations and feature contracts are
checked separately, not replaced by counting cmap entries.
"""
from __future__ import annotations
import hashlib,io,json,sys,tempfile,subprocess,unicodedata as ud
from pathlib import Path
from functools import lru_cache
from fontTools.ttLib import TTFont
from shapely.affinity import affine_transform,translate
from shapely.ops import unary_union
from shapely.geometry import LineString
import ots,uharfbuzz as hb
from build import ROOT,FULL,OUT,FAMILIES,CORE,load,sha,compile_font,signature
sys.path.insert(0,str(ROOT/'design/core-01/tools'))
from geometry import inspect,component_count
SPACES={0,13,32,0xA0,0xAD,*range(0x2000,0x200C),0x202F,0x2060,0xFEFF}
FEATURES=set('case ccmp dlig dnom frac kern liga mark mkmk numr ordn pnum ss01 ss02 ss03 ss04 ss05 subs sups tnum zero'.split())
DIGITS=['zero','one','two','three','four','five','six','seven','eight','nine']
COUNTERS={**dict.fromkeys('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',0),**{c:1 for c in 'ADOPQRabdeopq'},'B':2,'O':1,'a':1,'e':1,'zero':1,'four':1,'six':1,'eight':2,'nine':1}

class Shaper:
    def __init__(self,font):
        font.flavor=None;buf=io.BytesIO();font.save(buf);self.names=font.getGlyphOrder()
        self.face=hb.Face(buf.getvalue());self.font=hb.Font(self.face);self.font.scale=(1000,1000);hb.ot_font_set_funcs(self.font)
    def shape(self,text,features=None):
        b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(self.font,b,features or {})
        return [{'glyph':self.names[i.codepoint],'advance':p.x_advance,'x':p.x_offset,'y':p.y_offset} for i,p in zip(b.glyph_infos,b.glyph_positions)]

def assert_shapes(shaper):
    tests=[]
    def expect(text,features,names):
        r=shaper.shape(text,features);actual=[x['glyph'] for x in r]
        if actual!=names:raise ValueError(f'Shaping mismatch {text!r} {features}: {actual} != {names}')
        tests.append({'text':text,'features':features,'glyphs':actual})
    expect('office',{'liga':True},['o','f_f_i','c','e'])
    expect('fi',{'liga':False},['f','i'])
    expect('á',{'ss01':True},['uni00E1.ss01'])
    expect('g',{'ss02':True},['g.double'])
    expect('yij',{'ss03':True},['y.diagonal','i.cut','j.cut'])
    expect('R',{'ss04':True},['R.curved'])
    expect('Il',{'ss05':True},['I.clarity','l.clarity'])
    expect('0',{'zero':True,'tnum':True},['zero.slash.tnum'])
    expect('12/34',{'frac':True},['one.numr','two.numr','fraction','three.dnom','four.dnom'])
    expect('123',{'sups':True},['one.sups','two.sups','three.sups'])
    expect('123',{'subs':True},['one.subs','two.subs','three.subs'])
    expect('st',{'dlig':True},['s_t'])
    for text in ('d\u030c','t\u030c','l\u030c','L\u030c'):
        cp=ord(ud.normalize('NFC',text));expect(text,{},[f'uni{cp:04X}'])
    tab=shaper.shape('0123456789',{'tnum':True});assert len(set(x['advance'] for x in tab))==1
    tests.append({'text':'0123456789','test':'equal tabular advances','advance':tab[0]['advance']})
    av=shaper.shape('AV',{'kern':True});off=shaper.shape('AV',{'kern':False});assert sum(x['advance'] for x in av)<sum(x['advance'] for x in off)
    avaccent=shaper.shape('ÁV',{'kern':True});assert [r['advance'] for r in avaccent]==[r['advance'] for r in av]
    tests.append({'text':'AV / ÁV','test':'accent-aware kerning','advances':[r['advance'] for r in av]})
    for text,direction in [('x\u0301\u0301',1),('x\u0323\u0323',-1)]:
        r=shaper.shape(text);assert len(r)==3 and r[1]['advance']==r[2]['advance']==0
        assert (r[2]['y']-r[1]['y'])*direction>0 and r[1]['y']*direction>0
        tests.append({'text':text,'test':'mark-to-mark stacking','positions':r})
    # Unsupported scripts stay unsupported; never silently substitute a source.
    assert all(r['glyph']=='.notdef' for r in shaper.shape('中文'))
    tests.append({'text':'中文','test':'explicit unsupported-script boundary'})
    return tests

def source_check(family,target):
    u=load(family);cmap={cp:g.name for g in u for cp in g.unicodes}
    assert set(cmap)==set(map(int,target['cmap'])),family+' coverage drift'
    helpers=json.loads((FULL/'helper-glyphs.json').read_text())
    assert set(u.keys())==set(target['glyph_order'])|set(helpers['glyphs']),family+' feature/helper inventory drift'
    @lru_cache(None)
    def geom(n):return inspect(u[n],u)
    records=[]
    for n in u.keys():
        g=u[n];r=geom(n)
        assert r['valid'],(family,n,'invalid source contour')
        if g.unicodes and any(cp not in SPACES for cp in g.unicodes):assert not r['geometry'].is_empty,(family,n,'missing ink')
        for comp in g.components:assert comp.baseGlyph in u,(n,'unknown component')
        if n in COUNTERS:
            expected=1 if n=='g' and family=='LihuiT' else 2 if n=='g' else COUNTERS[n]
            assert r['counter_contours']==expected,(family,n,'unexpected counters',r['counter_contours'],expected)
        if n=='g':assert r['counter_contours']==(1 if family=='LihuiT' else 2)
        if n in ('i','j'):assert component_count(r['geometry'])==2
        if n in list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')+DIGITS and n not in ('i','j'):
            assert component_count(r['geometry'])==1,(family,n,'disconnected primary glyph')
        if n=='uni2318':assert r['counter_contours']==5,(family,'command sign must have four loops and one central counter')
        if n.startswith('uni') and any(c.baseGlyph=='uni0328' for c in g.components) and n!='uni02DB':
            base=g.components[0].baseGlyph
            expected_parts=component_count(geom(base)['geometry'])+sum(c.baseGlyph!='uni0328' for c in g.components[1:])
            assert component_count(r['geometry'])==expected_parts,(family,n,'ogonek tail must join its base, not float')
        # No off-screen source glyphs hidden by arbitrary line metrics.
        if not r['geometry'].is_empty:
            _,y0,_,y1=r['geometry'].bounds
            assert y1<=u.info.openTypeOS2WinAscent and -y0<=u.info.openTypeOS2WinDescent,(family,n,'metric clipping')
        records.append({'glyph':n,'valid':True,'components':len(g.components),'source_cubics':r['cubics']})
    collisions=[];mark_pairs=0
    for g in u:
        if len(g.components)<2:continue
        pieces=[]
        for c in g.components:
            xx,yx,xy,yy,dx,dy=c.transformation
            pieces.append((c.baseGlyph,affine_transform(geom(c.baseGlyph)['geometry'],[xx,xy,yx,yy,dx,dy])))
        for i,(n,shape) in enumerate(pieces[1:],1):
            cls=u[n].lib.get('de.zayju.markClass')
            if cls not in ('top','bottom') and n!='caron.right':continue
            for other,base in pieces[:i]:
                mark_pairs+=1
                if shape.intersection(base).area>.05:collisions.append((g.name,n,other))
    assert not collisions,(family,'unexpected nonjoining mark collisions',collisions)
    if family=='LihuiT':
        # Regressions found during real alphabet review: crossbar returns cannot
        # turn the lower stem into a triangular wedge.
        for n,y,expected in [('F',140,88),('f',140,87),('t',200,87),('four',90,88)]:
            cut=geom(n)['geometry'].intersection(LineString([(-50,y),(800,y)]))
            assert abs(cut.length-expected)<.15,(n,'incorrect crossbar/stem return')
    return u,{'family':family,'glyphs':len(u),'codepoints':len(cmap),'approved_core_unchanged':True,'all_source_valid':True,'nonjoining_mark_pairs_checked':mark_pairs,'mark_collisions':[], 'records':records}

def forced_decomposition_check(font_path):
    """Remove precomposed cmap entries in memory so HarfBuzz cannot normalize
    both inputs to the same precomposed glyph and conceal broken mark anchors.
    Compare actual positioned outlines against the original precomposed forms.
    Never writes the modified test font to disk or changes source files.
    """
    with TTFont(font_path) as original,TTFont(font_path) as modified:
        cmap=original.getBestCmap()
        pairs={cp:ud.normalize('NFD',chr(cp)) for cp in cmap if len(ud.normalize('NFD',chr(cp)))>1 and all(ord(c) in cmap for c in ud.normalize('NFD',chr(cp)))}
        for table in modified['cmap'].tables:
            if table.isUnicode():
                for cp in pairs:table.cmap.pop(cp,None)
        normal=Shaper(original);decomposed=Shaper(modified);gs=original.getGlyphSet()
        @lru_cache(None)
        def geom(name):return inspect(gs[name],gs)['geometry']
        def assemble(items):
            x=0;pieces=[]
            for item in items:
                if item['glyph']=='.notdef':raise ValueError('Forced decomposition fell back')
                pieces.append(translate(geom(item['glyph']),xoff=x+item['x'],yoff=item['y']));x+=item['advance']
            return unary_union(pieces),x
        worst={'codepoint':None,'feature':None,'sampled_distance_upm':0};failures=[];feature_counts={}
        for feature in ('default','ss01','ss02','ss03','ss04','ss05'):
            settings={'kern':False}
            if feature!='default':settings[feature]=True
            feature_counts[feature]=0
            for cp,text in pairs.items():
                a,aa=assemble(normal.shape(chr(cp),settings));b,ba=assemble(decomposed.shape(text,settings))
                distance=a.boundary.hausdorff_distance(b.boundary);feature_counts[feature]+=1
                if distance>worst['sampled_distance_upm']:worst={'codepoint':f'U+{cp:04X}','feature':feature,'sampled_distance_upm':round(distance,6)}
                if distance>1.6 or aa!=ba:failures.append({'cp':f'U+{cp:04X}','feature':feature,'distance':distance,'advances':[aa,ba]})
        if failures:raise ValueError(('Broken forced decomposed mark/feature placement',failures[:12]))
        return {'pairs_checked':sum(feature_counts.values()),'characters_per_feature':len(pairs),'feature_comparisons':feature_counts,'precomposed_cmap_removed_in_memory':True,'max':worst,'failures':[]}

def main():
    target=json.loads((FULL/'repertoire.json').read_text());build=json.loads((OUT/'build.json').read_text())
    assert build['stage']=='full-reference-review','Partial previews cannot satisfy the full gate'
    for name,value in build['source_inputs'].items():assert sha(ROOT/name)==value,('stale build source',name)
    report={'scope':'Two completed reference cuts only; new drawings await final visual review. No extra weights, publication, installation or full-Unicode claim.','source':[],'files':[],'conversion':[],'forced_decomposition':[]}
    sources={}
    for family in FAMILIES:
        u,result=source_check(family,target);sources[family]=u;report['source'].append(result)
        print('Source:',family,result['glyphs'],'glyphs, core unchanged; mark clearance passed',flush=True)
    sanitizer=Path(ots.__file__).with_name('ots-sanitize')
    with tempfile.TemporaryDirectory(prefix='full-ots-',dir=OUT) as temp:
      for i,row in enumerate(build['records']):
        path=OUT/row['file'];assert sha(path)==row['sha256']
        proc=subprocess.run([str(sanitizer),str(path),str(Path(temp)/f'{i}.sfnt')],capture_output=True,text=True)
        assert proc.returncode==0,(path.name,proc.stdout,proc.stderr)
        with TTFont(path,checkChecksums=2) as f:
            cmap=f.getBestCmap();assert set(cmap)==set(map(int,target['cmap']))
            assert f['name'].getDebugName(9)=='zayju';assert f['name'].getDebugName(13)==(ROOT/'OFL.txt').read_text().strip()
            assert 'Full Draft' in f['name'].getDebugName(1) and f['OS/2'].usWeightClass==400 and f['post'].italicAngle==0 and 'fvar' not in f
            features=set(rec.FeatureTag for tag in ('GSUB','GPOS') for rec in f[tag].table.FeatureList.FeatureRecord)
            assert features>=FEATURES
            gs=f.getGlyphSet();findings=[];curve_count=0
            for n in f.getGlyphOrder():
                r=inspect(gs[n],gs);curve_count+=r['cubics']+r['quadratics']
                if not r['valid']:findings.append(n)
                if any(cp not in SPACES for cp,name in cmap.items() if name==n):assert not r['geometry'].is_empty,(path.name,n,'empty encoded glyph')
            assert not findings,(path.name,'serialized contour failures',findings)
            if 'glyf' in f:
                for name in f.getGlyphOrder():
                    glyph=f['glyf'][name]
                    if glyph.isComposite():
                        assert all(not f['glyf'][c.glyphName].isComposite() for c in glyph.components),(name,'nested output component')
                assert bytes(f['prep'].program.getBytecode())==bytes.fromhex('b801ff85b0048d')
            shaper=Shaper(f);tests=assert_shapes(shaper);canonical=0;encoded=0
            for cp in cmap:
                if cp not in SPACES:
                    result=shaper.shape(chr(cp));assert result and all(r['glyph']!='.notdef' for r in result),(path.name,hex(cp))
                    encoded+=1
                nfd=ud.normalize('NFD',chr(cp))
                if len(nfd)>1 and all(ord(c) in cmap for c in nfd):
                    assert shaper.shape(chr(cp))==shaper.shape(nfd),(path.name,hex(cp),'NFC/NFD mismatch')
                    canonical+=1
            caret=f['GDEF'].table.LigCaretList;assert caret is not None
            for n,g in zip(caret.Coverage.glyphs,caret.LigGlyph):
                assert [c.Coordinate for c in g.CaretValue]==sources[row['family']].lib['de.zayju.ligatureCarets'][n]
            assert len(caret.Coverage.glyphs)==7
            info={**row,'ots':'passed','serialized_glyphs_checked':len(gs),'curves':curve_count,'features':sorted(features),'layout_regressions':tests,'encoded_character_checks':encoded,'canonical_equivalence_checks':canonical,'ligature_carets_checked':7}
            report['files'].append(info);print(path.name,encoded,'encoded shapes,',canonical,'canonical pairs,',len(tests),'layout checks passed',flush=True)
    for row in build['records']:
        result=forced_decomposition_check(OUT/row['file'])
        report['forced_decomposition'].append({'file':row['file'],'sha256':row['sha256'],**result})
        print(row['file'],result['pairs_checked'],'forced-decomposed outline comparisons passed',flush=True)
    for family in FAMILIES:
        paths={fmt:OUT/'fonts'/f'{family}FullDraft-Reference.{fmt}' for fmt in ('ttf','otf','woff2')}
        with TTFont(paths['ttf']) as a,TTFont(paths['otf']) as b,TTFont(paths['woff2']) as w:
            ga,gb=a.getGlyphSet(),b.getGlyphSet();distances=[]
            assert a['hmtx'].metrics==w['hmtx'].metrics and a.getBestCmap()==w.getBestCmap()
            for n in a.getGlyphOrder():
                assert a['glyf'][n].getCoordinates(a['glyf'])==w['glyf'][n].getCoordinates(w['glyf'])
                x=inspect(ga[n],ga)['geometry'];y=inspect(gb[n],gb)['geometry']
                if x.is_empty and y.is_empty:distance=0
                else:distance=x.boundary.segmentize(2).hausdorff_distance(y.boundary.segmentize(2))
                distances.append({'glyph':n,'sampled_distance_upm':round(distance,6)})
            failures=[r for r in distances if r['sampled_distance_upm']>1.6]
            report['conversion'].append({'family':family,'woff2_lossless':True,'gate_upm':1.6,'max':max(distances,key=lambda r:r['sampled_distance_upm']),'findings':failures,'records':distances})
            print(family,'cross-format max:',max(distances,key=lambda r:r['sampled_distance_upm']),'failures',len(failures),flush=True)
    report['passed']=all(not r['findings'] for r in report['conversion'])
    report['source_inputs']=build['source_inputs']
    (OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if not report['passed']:raise SystemExit('Cross-format geometry differs; inspect findings before acceptance')
    print('PASS full reference source, coverage, layout and serialized outline gates; final optical review remains separate.')
if __name__=='__main__':main()
