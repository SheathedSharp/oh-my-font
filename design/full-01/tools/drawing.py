"""Small authoring utilities: preserve drawn cubic contours, do not generate letters.

Authoritative shapes are stored in UFO GLIF files. This utility normalizes winding
and refuses malformed paths and accidental overwrites; it is not a skeleton,
weight interpolator, outline buffer, or production build dependency.
"""
from pathlib import Path
import sys
from fontTools.svgLib.path import parse_path
from fontTools.pens.recordingPen import RecordingPen,replayRecording
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.pointPen import SegmentToPointPen
from shapely.geometry import Polygon
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'design/core-01/tools'))
from geometry import FlattenPen

def normalize(path):
    r=RecordingPen();parse_path(path,r);parts=[];current=[]
    for op,args in r.value:
        current.append((op,args))
        if op=='endPath':raise ValueError('Open outline')
        if op=='closePath':parts.append(current);current=[]
    if current:raise ValueError('Unclosed outline')
    polygons=[]
    for part in parts:
        pen=FlattenPen(flatness=.04);replayRecording(part,pen)
        polygon=Polygon(pen.contours[0])
        if not polygon.is_valid or polygon.area<.01:raise ValueError('Invalid/degenerate authored contour')
        polygons.append(polygon)
    result=RecordingPen()
    for i,part in enumerate(parts):
        nesting=sum(p.covers(polygons[i]) for j,p in enumerate(polygons) if j!=i)
        desired=1 if nesting%2==0 else -1
        area=AreaPen(None);replayRecording(part,area)
        replayRecording(part,ReverseContourPen(result) if area.value*desired<0 else result)
    return result

def add(u,name,width,path,cp=None,note='',replace=False):
    if name in u and not replace:raise ValueError('Refusing to overwrite '+name)
    r=normalize(path)
    g=u[name] if name in u else u.newGlyph(name)
    g.clearContours();g.clearComponents();g.width=width;g.unicodes=[] if cp is None else [cp]
    r.replay(SegmentToPointPen(g.getPointPen(),guessSmooth=True));g.note=note
    g.lib['de.zayju.designStatus']='new-reference-drawing-awaiting-full-review'
    return g
