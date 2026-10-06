"""Renderer-independent outline inspection for source and compiled glyphs.

Coordinates are flattened only for QA, never written back into a font. The
flatness below is a sampled inspection precision, not an analytic error proof.
"""
from math import hypot, isfinite
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union

class FlattenPen(BasePen):
    def __init__(self, glyph_set=None, flatness=.08):
        super().__init__(glyph_set)
        self.flatness=flatness;self.contours=[];self.current=[]
        self.cubics=0;self.quadratics=0;self.lines=0
    def _moveTo(self,p):
        self.current=[tuple(p)]
    def _lineTo(self,p):
        self.lines+=1
        if tuple(p)!=self.current[-1]:self.current.append(tuple(p))
    def _curveToOne(self,a,b,c):
        self.cubics+=1;self._flatten(self.current[-1],a,b,c)
    def _qCurveToOne(self,a,b):
        self.quadratics+=1;p=self.current[-1]
        self._flatten(p,((p[0]+2*a[0])/3,(p[1]+2*a[1])/3),((b[0]+2*a[0])/3,(b[1]+2*a[1])/3),b)
    def _flatten(self,p,a,b,c,depth=0):
        dx=c[0]-p[0];dy=c[1]-p[1];n=hypot(dx,dy)
        error=max(abs(dx*(q[1]-p[1])-dy*(q[0]-p[0]))/n for q in (a,b)) if n>1e-12 else max(hypot(q[0]-p[0],q[1]-p[1]) for q in (a,b))
        if error<=self.flatness or depth>=18:
            if tuple(c)!=self.current[-1]:self.current.append(tuple(c))
            return
        mid=lambda x,y:((x[0]+y[0])/2,(x[1]+y[1])/2)
        ab,bc,cd=mid(p,a),mid(a,b),mid(b,c)
        abc,bcd=mid(ab,bc),mid(bc,cd);m=mid(abc,bcd)
        self._flatten(p,ab,abc,m,depth+1);self._flatten(m,bcd,cd,c,depth+1)
    def _closePath(self):
        if self.current and self.current[-1]!=self.current[0]:self.current.append(self.current[0])
        self.contours.append(self.current);self.current=[]
    def _endPath(self):
        raise ValueError('Open font contour')

def inspect(outline, glyph_set=None, flatness=.08):
    pen=FlattenPen(glyph_set,flatness);outline.draw(pen)
    outside=[];inside=[];invalid=[];degenerate=[];signed=[]
    for index,points in enumerate(pen.contours):
        if not all(isfinite(v) for p in points for v in p):raise ValueError('Non-finite outline coordinate')
        if len(points)<4:
            degenerate.append(index);continue
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]))/2
        poly=Polygon(points)
        if not poly.is_valid:invalid.append(index)
        if abs(area)<.02:degenerate.append(index)
        signed.append((area,poly))
    # Never conceal invalid inputs with buffer(0). Callers can retain the invalid
    # record and decide whether a deliberately exact touching join needs review.
    exterior_sign=1 if not signed or max(signed,key=lambda item:abs(item[0]))[0]>0 else -1
    for area,polygon in signed:
        (outside if area*exterior_sign>0 else inside).append(polygon)
    valid=not invalid and not degenerate
    geometry=None
    if valid:
        geometry=unary_union(outside).difference(unary_union(inside)) if outside else GeometryCollection()
        valid=geometry.is_valid
    return {'pen':pen,'geometry':geometry,'valid':valid,'invalid_contours':invalid,'degenerate_contours':degenerate,
            'outer_contours':len(outside),'counter_contours':len(inside),
            'cubics':pen.cubics,'quadratics':pen.quadratics,'lines':pen.lines}

def component_count(g):
    if g is None:return None
    if g.is_empty:return 0
    return 1 if isinstance(g,Polygon) else len([p for p in g.geoms if isinstance(p,Polygon)])
