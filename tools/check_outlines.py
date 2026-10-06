#!/usr/bin/env python3
"""Audit every independent master and every compiled font's glyph inventory.

Includes explicit light-weight junction regressions. The report distinguishes
source geometry from integer-grid compiled outlines and retains every finding;
this is not a claim that every glyph has received human optical approval.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from masters import Designer, WEIGHTS
from fontTools.ttLib import TTFont
from outline_qa import inspect,component_count
from shapely.geometry import LineString,box


def source_check(family,weight,oblique):
    d=Designer(family,weight,oblique).build();bad=[];total_curves=0;total_contours=0;core={}
    for name,g in d.glyphs.items():
        r=inspect(g.geometry)
        total_curves+=r['cubics'];total_contours+=len(r['pen'].contours)
        if not r['valid']:
            bad.append({'glyph':name,'invalid_contours':r['invalid_contours'],'degenerate_contours':r['degenerate_contours']})
        if name in ('n','m','h','e','R','o','g','y','a'):core[name]=r
    checks=[]
    def check(name,ok,**details):checks.append({'check':name,'passed':bool(ok),**details})
    check('stored cubic contours present',total_curves>1000,cubic_segments=total_curves)
    if weight in (100,300,400):
        check('e is connected with one counter',component_count(core['e']['geometry'])==1 and core['e']['counter_contours']==1)
        # Test upright design coordinates; oblique is tested independently through
        # full glyph validation and the exact shear-isolation unit test.
        if not oblique:
            for char,count in [('n',2),('h',2),('m',3)]:
                geom=core[char]['geometry'];samples=[]
                for y in (1,5,12,24):
                    cut=geom.intersection(LineString([(-100,y),(2000,y)]))
                    segments=list(cut.geoms) if hasattr(cut,'geoms') else [cut]
                    widths=sorted(g.length for g in segments if g.length>.01)
                    samples.append(widths)
                check(f'{char}: straight stem feet',all(len(w)==count and all(abs(x-d.t)<.6 for x in w) for w in samples),widths=samples,expected_stroke=d.t)
            # R's leg must not protrude into its own counter above the lower bar.
            r=core['R'];w=700*(.905 if d.text else 1)
            y=d.cap*.39+d.t*.82+2
            # Center of the previous erroneous leg start in 0.301.
            probe=box(d.sb+w*.46-1,y,d.sb+w*.49+1,d.cap*.45+2)
            if y<d.cap*.45+2:
                check('R: no counter spur',r['geometry'].intersection(probe).area<.1)
        for char in ('n','m','h','e','R','o','g','a'):
            check(f'{char}: connected primary shape',component_count(core[char]['geometry'])==1)
        # Open y is deliberately two strokes in both families; do not force union.
        check('y: intentional two components',component_count(core['y']['geometry'])==2)
    return {'family':family,'weight':weight,'style':'oblique' if oblique else 'upright','glyphs':len(d.glyphs),'codepoints':len(d.cmap),
            'contours':total_contours,'cubic_segments':total_curves,'invalid':bad,'regressions':checks,
            'source_sha256':hashlib.sha256(d.source_path.read_bytes()).hexdigest()}


def compiled_check(path):
    findings=[];segments={'cubics':0,'quadratics':0,'lines':0};points=0
    with TTFont(path) as font:
        gs=font.getGlyphSet()
        for name in font.getGlyphOrder():
            r=inspect(gs[name],gs)
            for key in segments:segments[key]+=r[key]
            points+=sum(len(c) for c in r['pen'].contours)
            if not r['valid']:
                findings.append({'glyph':name,'invalid_contours':r['invalid_contours'],'degenerate_contours':r['degenerate_contours']})
        required='cubics' if 'CFF ' in font else 'quadratics'
        return {'file':path.relative_to(ROOT/'dist').as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'glyphs':len(gs),'codepoints':len(font.getBestCmap()),'curve_segments':segments,
                'native_curve_type_present':segments[required]>1000,'findings':findings}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-only',action='store_true');p.add_argument('--weights',nargs='+',type=int,choices=list(WEIGHTS),default=list(WEIGHTS))
    p.add_argument('--report',type=Path,default=ROOT/'.release-work/outline-checks.json')
    a=p.parse_args();start=time.monotonic();report={'precision_upm':.08,'scope':'all source glyphs plus compiled outline geometry; not exhaustive human optical approval','source':[],'compiled':[]}
    for family in ('LihuiT','zayJu'):
      for weight in a.weights:
       for oblique in (False,True):
        r=source_check(family,weight,oblique);report['source'].append(r)
        print(f"{family} {weight} {r['style']}: {len(r['invalid'])} invalid source glyphs, {sum(not x['passed'] for x in r['regressions'])} regression failures",flush=True)
    if not a.source_only:
        paths=sorted((ROOT/'dist').glob('*/*/*.*'))
        paths=[p for p in paths if p.suffix in ('.ttf','.otf','.woff2')]
        if len(paths)!=96:raise SystemExit('Expected all 96 compiled fonts')
        for path in paths:
            r=compiled_check(path);report['compiled'].append(r)
            print(f"{r['file']}: {len(r['findings'])} compiled geometric findings",flush=True)
    report['seconds']=round(time.monotonic()-start,2)
    report['source_passed']=all(not r['invalid'] and all(x['passed'] for x in r['regressions']) for r in report['source'])
    report['compiled_passed']=all(r['native_curve_type_present'] and not r['findings'] for r in report['compiled'])
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['source_passed'] and report['compiled_passed'] else 1
if __name__=='__main__':sys.exit(main())
