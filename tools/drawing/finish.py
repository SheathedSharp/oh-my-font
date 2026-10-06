"""Remove exact zero-width backtracks from decimalized draft line contours.

A diagonal terminal cutter in the historical scaffold leaves an extremely thin
line excursion along the baseline. Decimal serialization makes it exactly zero
width. Remove only the reversing collinear vertex: no surviving point moves,
no filled area changes, and neither curves nor genuine corners are smoothed.
This is a source editing helper, never imported by the production build.
"""
from fontTools.pens.recordingPen import RecordingPen,replayRecording
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.svgLib.path import parse_path
from shapely.geometry import Polygon

def finish_svg(text):
    recording=RecordingPen();parse_path(text,recording);result=[];current=[];repaired=0
    for op,args in recording.value:
        current.append((op,args))
        if op!='closePath':continue
        if all(verb in ('moveTo','lineTo','closePath') for verb,_ in current):
            points=[p[0] for verb,p in current if verb!='closePath']
            if points[-1]==points[0]:points.pop()
            polygon=Polygon(points)
            if not polygon.is_valid:
                changed=True
                while changed and len(points)>3:
                    changed=False
                    for i,b in enumerate(points):
                        a=points[i-1];c=points[(i+1)%len(points)]
                        u=(b[0]-a[0],b[1]-a[1]);v=(c[0]-b[0],c[1]-b[1])
                        cross=u[0]*v[1]-u[1]*v[0];dot=u[0]*v[0]+u[1]*v[1]
                        if abs(cross)<1e-10 and dot<=0:
                            del points[i];changed=True;break
                fixed=Polygon(points)
                if not fixed.is_valid or abs(polygon.area-fixed.area)>1e-7:
                    raise ValueError('Not an exact zero-width line backtrack; requires glyph review')
                current=[('moveTo',(points[0],)),*[('lineTo',(p,)) for p in points[1:]],('closePath',())]
                repaired+=1
        result.extend(current);current=[]
    if current:raise ValueError('Unclosed source contour')
    pen=SVGPathPen(None);replayRecording(result,pen)
    return pen.getCommands(),repaired
