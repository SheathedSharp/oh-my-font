"""Conservative polygon-to-cubic migration, not a font-build postprocessor.

Uses the pinned beziers fitter, with explicit corner/straight-edge partitioning,
constrained tangents, and an independent sampled Hausdorff/topology acceptance
check. Keeps a rejected contour as lines and records that fact; never silently
accepts a missing/simplified component. Source masters remain editable afterward.
"""
from functools import lru_cache
from math import acos, degrees, hypot
from beziers.point import Point
from beziers.utils.curvefitter import CurveFit
from shapely.geometry import Polygon, LineString

TOLERANCE = .22
FLATNESS = .02


def unit(v):
    n=hypot(*v)
    return (v[0]/n,v[1]/n) if n>1e-12 else (1.,0.)


def flatten_cubic(p0,p1,p2,p3, out, depth=0):
    dx=p3[0]-p0[0];dy=p3[1]-p0[1];n=hypot(dx,dy)
    err=max(abs(dx*(p[1]-p0[1])-dy*(p[0]-p0[0]))/n for p in (p1,p2)) if n>1e-12 else max(hypot(p[0]-p0[0],p[1]-p0[1]) for p in (p1,p2))
    if err <= FLATNESS or depth>=16:
        out.append(p3);return
    mid=lambda a,b:((a[0]+b[0])/2,(a[1]+b[1])/2)
    a,b,c=mid(p0,p1),mid(p1,p2),mid(p2,p3)
    d,e=mid(a,b),mid(b,c);m=mid(d,e)
    flatten_cubic(p0,a,d,m,out,depth+1);flatten_cubic(m,e,c,p3,out,depth+1)


def points_for(commands):
    out=[]
    for op, pts in commands:
        if op in ('moveTo','lineTo'):out.append(pts[0])
        elif op=='curveTo':flatten_cubic(out[-1],*pts,out)
    return out


def lines(points):
    return [('moveTo',(points[0],)),*[('lineTo',(p,)) for p in points[1:]],('closePath',())]


@lru_cache(maxsize=32768)
def fit_normalized(points):
    n=len(points)
    if n<3:raise ValueError('Degenerate input contour')
    edges=[(points[(i+1)%n][0]-points[i][0],points[(i+1)%n][1]-points[i][1]) for i in range(n)]
    lengths=[hypot(*e) for e in edges]
    sharp=set();cuts=set();long=set()
    for i in range(n):
        a,b=unit(edges[i-1]),unit(edges[i])
        angle=degrees(acos(max(-1.,min(1.,a[0]*b[0]+a[1]*b[1]))))
        if angle>24:sharp.add(i);cuts.add(i)
        if lengths[i]>26:
            long.add(i);cuts.update((i,(i+1)%n))
    if len(cuts)<2:
        for axis in (0,1):
            cuts.add(min(range(n),key=lambda i:points[i][axis]))
            cuts.add(max(range(n),key=lambda i:points[i][axis]))
    cuts=sorted(cuts);commands=[('moveTo',(points[cuts[0]],))];partial_preservation=False
    try:
        for start,end in zip(cuts,cuts[1:]+[cuts[0]+n]):
            ids=list(range(start,end+1));part=[points[i%n] for i in ids]
            if len(part)==2:
                commands.append(('lineTo',(part[-1],)));continue
            def tangent(i,forward):
                i%=n
                if i in sharp:v=edges[i] if forward else edges[i-1]
                elif i-1 in long or (i-1)%n in long:v=edges[i-1]
                elif i in long:v=edges[i]
                else:
                    a,b=unit(edges[i-1]),unit(edges[i]);v=(a[0]+b[0],a[1]+b[1])
                v=unit(v)
                return Point(v[0],v[1]) if forward else Point(-v[0],-v[1])
            # Pinned 0.6.0 accepts SQUARED positional error. Private entry point
            # is intentionally isolated here to constrain both endpoint tangents.
            segs=CurveFit._fitCurve([Point(*p) for p in part],tangent(start,True),tangent(end,False),TOLERANCE**2,.5,256)
            if not segs:raise ValueError('Curve fitter exhausted its segment budget')
            if hypot(segs[-1][-1].x-part[-1][0],segs[-1][-1].y-part[-1][1])>1e-6:raise ValueError('Incomplete fit')
            proposed=[('curveTo',tuple((round(p.x,5),round(p.y,5)) for p in list(seg)[1:])) for seg in segs]
            sampled=LineString(points_for([('moveTo',(part[0],)),*proposed]))
            original_part=LineString(part)
            local_error=original_part.segmentize(1).hausdorff_distance(sampled.segmentize(1))
            if not sampled.is_simple or local_error>.30:
                # Preserve only this rejected local span, not every otherwise
                # valid cubic in a complex reference-led contour.
                commands.extend(('lineTo',(point,)) for point in part[1:])
                partial_preservation=True
            else:
                commands.extend(proposed)
        commands.append(('closePath',()))
        original=Polygon(points);new=Polygon(points_for(commands))
        # Dense boundary samples guard both directions, beyond fitter input nodes.
        error=original.boundary.segmentize(1).hausdorff_distance(new.boundary.segmentize(1))
        if not new.is_valid or error>.35 or abs(new.area-original.area)>max(1,original.length*.35):
            raise ValueError('Independent geometry guard rejected fit')
        return tuple(commands),round(error,6),partial_preservation
    except (ValueError,ZeroDivisionError,RecursionError,TypeError):
        return tuple(lines(points)),0.,True


def fit_contour(points):
    x0=min(x for x,y in points);y0=min(y for x,y in points)
    normalized=tuple((round(x-x0,5),round(y-y0,5)) for x,y in points)
    commands,error,fallback=fit_normalized(normalized)
    return [(op,tuple((round(x+x0,4),round(y+y0,4)) for x,y in pts)) for op,pts in commands],error,fallback
