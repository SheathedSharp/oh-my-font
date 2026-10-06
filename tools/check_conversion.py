#!/usr/bin/env python3
"""Compare actual serialized TTF/CFF geometry and lossless WOFF2 outlines.

This is a dense sampled boundary-distance check, not an analytic Hausdorff proof.
A 1.6 UPM gate includes cu2qu approximation, TrueType integer rounding and the
curve-preserving overlap cleanup. It must not be confused with cu2qu's .25 UPM
pre-quantization error setting.
"""
import hashlib,json,sys,time
from pathlib import Path
from fontTools.ttLib import TTFont
import numpy as np
from shapely import STRtree, get_parts, get_coordinates, linestrings, points
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from outline_qa import inspect

def indexed_boundary_distance(a,b,spacing=2):
    """Same dense directed point-to-boundary distances, indexed by GEOS STRtree.

    Brute-force dense Hausdorff comparisons repeated for 30,240 glyph pairs
    made the gate unnecessarily slow. Index segments, not just their endpoints,
    so the nearest distances and the sampling contract remain unchanged.
    """
    def index(boundary):
        edges=[]
        for part in get_parts(boundary):
            c=get_coordinates(part)
            if len(c)>1:edges.append(np.stack((c[:-1],c[1:]),axis=1))
        return STRtree(linestrings(np.concatenate(edges)))
    aa=a.boundary;bb=b.boundary
    samples_a=points(get_coordinates(aa.segmentize(spacing)))
    samples_b=points(get_coordinates(bb.segmentize(spacing)))
    _,da=index(bb).query_nearest(samples_a,return_distance=True,all_matches=False)
    _,db=index(aa).query_nearest(samples_b,return_distance=True,all_matches=False)
    if len(da)!=len(samples_a) or len(db)!=len(samples_b):
        raise ValueError('Incomplete nearest-boundary query')
    return max(float(da.max()),float(db.max()))

def main():
    records=[];start=time.monotonic()
    paths=sorted((ROOT/'dist/ttf').glob('*/*.ttf'))
    if len(paths)!=32:raise SystemExit('Expected 32 TrueType faces')
    for path in paths:
        family=path.parent.name;post=path.stem
        otf=ROOT/'dist/otf'/family/(post+'.otf');woff=ROOT/'dist/woff2'/family/(post+'.woff2')
        with TTFont(path) as a,TTFont(otf) as b,TTFont(woff) as w:
            ga=a.getGlyphSet();gb=b.getGlyphSet();errors=[];maximum=(0.,None)
            lossless=(a.getBestCmap()==w.getBestCmap() and a.getGlyphOrder()==w.getGlyphOrder() and a['hmtx'].metrics==w['hmtx'].metrics)
            for name in a.getGlyphOrder():
                at=a['glyf'][name];wt=w['glyf'][name]
                lossless &= at.getCoordinates(a['glyf'])==wt.getCoordinates(w['glyf'])
                x=inspect(ga[name],ga)['geometry'];y=inspect(gb[name],gb)['geometry']
                if x is None or y is None:errors.append({'glyph':name,'reason':'invalid outline'});continue
                if x.is_empty and y.is_empty:continue
                if x.is_empty != y.is_empty:errors.append({'glyph':name,'reason':'disappearing glyph'});continue
                distance=indexed_boundary_distance(x,y)
                if distance>maximum[0]:maximum=(distance,name)
                if distance>1.6:errors.append({'glyph':name,'sampled_boundary_distance_upm':round(distance,6)})
            record={'family':family,'style':post,'glyphs_compared':len(ga),'woff2_lossless':bool(lossless),'max_sampled_distance_upm':round(maximum[0],6),'worst_glyph':maximum[1],'findings':errors,
                    'sha256':{p.suffix[1:]:hashlib.sha256(p.read_bytes()).hexdigest() for p in (path,otf,woff)}}
            records.append(record);print(f"{post}: distance={maximum[0]:.4f} UPM, WOFF2 lossless={lossless}, findings={len(errors)}",flush=True)
    report={'scope':__doc__,'gate_upm':1.6,'records':records,'seconds':round(time.monotonic()-start,2),'passed':all(r['woff2_lossless'] and not r['findings'] for r in records)}
    (ROOT/'.release-work/conversion-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['passed'] else 1
if __name__=='__main__':sys.exit(main())
