#!/usr/bin/env python3
"""Technical checks of only the proposed core, never visual approval or full-family QA."""
from __future__ import annotations
import hashlib,io,json,subprocess,sys,tempfile
from pathlib import Path
import glyphsLib,ufoLib2,ots,uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from build import STUDY,ROOT,CORE,FAMILIES,load_source,compile_source
from geometry import inspect,component_count

OUT=ROOT/'.release-work/core-01'
EXPECTED_HOLES={'B':2,'M':0,'R':1,'a':1,'e':1,'two':0,'three':0,'six':1,'eight':2,'nine':1}
SAMPLES=['BMR','age','23689','Rage','Mega','Rage  Mega','B a B e R a M e','2233668899']


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def shape(font_bytes,text):
    face=hb.Face(font_bytes);font=hb.Font(face);font.scale=(1000,1000);hb.ot_font_set_funcs(font)
    buf=hb.Buffer();buf.add_str(text);buf.guess_segment_properties();hb.shape(font,buf,{'kern':True})
    return [(i.codepoint,p.x_advance,p.x_offset,p.y_offset) for i,p in zip(buf.glyph_infos,buf.glyph_positions)]

def outlines_equal(a,b):
    x=inspect(a)['geometry'];y=inspect(b)['geometry']
    if x is None or y is None:return False
    if x.is_empty or y.is_empty:return x.is_empty and y.is_empty
    return x.boundary.hausdorff_distance(y.boundary)<.0001 and abs(x.area-y.area)<.001


def main():
    build=json.loads((OUT/'build.json').read_text());report={'scope':'22 proposed core glyphs only; all visual decisions remain unapproved','source':[],'files':[],'roundtrip':[],'cross_format':[]}
    for name,value in build['sources'].items():
        if digest(ROOT/name)!=value:raise ValueError('Stale build inputs: '+name)
    for family in FAMILIES:
        u,cmap=load_source(family);records=[]
        for char in CORE:
            name=cmap[ord(char)];g=u[name];r=inspect(g)
            holes=(1 if family=='LihuiT' else 2) if char=='g' else EXPECTED_HOLES[name]
            assert r['valid'] and component_count(r['geometry'])==1 and r['counter_contours']==holes,(family,name)
            assert r['cubics']>=8 and not g.components,(family,name,'Not an individually drawn curve glyph')
            assert r['geometry'].bounds[0]>=0 and r['geometry'].bounds[2]<=g.width,(family,name,'Sidebearings')
            # UFO3 is a per-glyph source: no generated composite or cross-master recipe.
            records.append({'character':char,'glyph':name,'cubic_segments':r['cubics'],'contours':len(r['pen'].contours),'holes':holes,'advance':g.width,'valid':True})
        report['source'].append({'family':family,'glyphs':records})
        gs=glyphsLib.GSFont(str(STUDY/'sources'/(family+'-Core01.glyphs')))
        back=glyphsLib.to_ufos(gs,ufo_module=ufoLib2,generate_GDEF=False)
        assert len(back)==1 and set(back[0].keys())==set(u.keys())
        for name in u.keys():
            assert back[0][name].width==u[name].width and back[0][name].unicodes==u[name].unicodes
            assert outlines_equal(u[name],back[0][name]),(family,name,'Glyphs companion drift')
        report['roundtrip'].append({'family':family,'ufo_glyphs_ufo_geometry_and_metrics':'passed','glyphs':13})
    sanitizer=Path(ots.__file__).with_name('ots-sanitize')
    with tempfile.TemporaryDirectory(prefix='core-ots-',dir=OUT) as temp:
        for index,row in enumerate(build['records']):
            path=OUT/row['file'];assert digest(path)==row['sha256']
            checked=subprocess.run([str(sanitizer),str(path),str(Path(temp)/f'{index}.sfnt')],capture_output=True,text=True)
            assert checked.returncode==0,(row['file'],checked.stdout,checked.stderr)
            with TTFont(path,checkChecksums=2) as f:
                assert set(f.getBestCmap())==set(map(ord,CORE+' ')) and len(f.getGlyphOrder())==13
                assert 'Core Study 01' in f['name'].getDebugName(1)
                assert f['name'].getDebugName(13)==(ROOT/'OFL.txt').read_text().strip()
                assert f['name'].getDebugName(9)=='zayju' and f['OS/2'].fsType==0
                assert 'fvar' not in f and f['post'].italicAngle==0
                glyphset=f.getGlyphSet();details=[]
                for name in f.getGlyphOrder():
                    r=inspect(glyphset[name],glyphset);assert r['valid'],(path.name,name)
                    if name not in ('space','.notdef'):
                        expected=(1 if row['family']=='LihuiT' else 2) if name=='g' else EXPECTED_HOLES[name]
                        assert component_count(r['geometry'])==1 and r['counter_contours']==expected,(path.name,name,'topology')
                        assert (r['cubics'] if 'CFF ' in f else r['quadratics'])>0
                    details.append({'glyph':name,'valid':True,'curves':r['cubics']+r['quadratics']})
                f.flavor=None;decoded=io.BytesIO();f.save(decoded);content=decoded.getvalue()
                for sample in SAMPLES:
                    shaped=shape(content,sample);assert all(gid>0 and advance>0 for gid,advance,_,_ in shaped)
                assert any(item[0]==0 for item in shape(content,'H')),'Missing glyph must remain missing'
            report['files'].append({**row,'ots':'passed','valid_glyphs':details,'shaping_samples_passed':len(SAMPLES),'unsupported_H_is_notdef':True})
    for family in FAMILIES:
        stem=family+'CoreStudy01-Reference'
        with TTFont(OUT/'fonts'/(stem+'.ttf')) as a,TTFont(OUT/'fonts'/(stem+'.otf')) as b,TTFont(OUT/'fonts'/(stem+'.woff2')) as w:
            ga,gb=a.getGlyphSet(),b.getGlyphSet();records=[]
            assert a['hmtx'].metrics==w['hmtx'].metrics and a.getBestCmap()==w.getBestCmap()
            for name in a.getGlyphOrder():
                assert a['glyf'][name].getCoordinates(a['glyf'])==w['glyf'][name].getCoordinates(w['glyf'])
                x=inspect(ga[name],ga)['geometry'];y=inspect(gb[name],gb)['geometry']
                if x.is_empty and y.is_empty:distance=0
                else:distance=x.boundary.segmentize(1).hausdorff_distance(y.boundary.segmentize(1))
                assert distance<1.5,(family,name,distance)
                records.append({'glyph':name,'sampled_distance_upm':round(distance,6)})
            report['cross_format'].append({'family':family,'ttf_cff':records,'woff2_lossless':True,'distance_scope':'sampled at <=1 UPM boundary spacing, not an analytic maximum proof'})
    # Recompile each format without reading any previous font; compare bytes.
    rebuilt=[]
    for row in build['records']:
        u,cmap=load_source(row['family']);f,_=compile_source(u,cmap,row['format']=='otf')
        f.flavor='woff2' if row['format']=='woff2' else None;buf=io.BytesIO();f.save(buf)
        assert hashlib.sha256(buf.getvalue()).hexdigest()==row['sha256']
        rebuilt.append({'file':row['file'],'identical':True})
    report['rebuild']=rebuilt;report['sources']=build['sources'];report['passed']=True
    text=json.dumps(report,indent=2)+'\n';assert '/Users/' not in text and '/home/' not in text
    (OUT/'checks.json').write_text(text);print('PASS: 22 core drawings, 6 compiled files, 48 shaping samples, Glyphs/UFO roundtrip and identical rebuilds. Visual acceptance remains pending.')
if __name__=='__main__':main()
