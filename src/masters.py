"""Production loader for independently editable, static cubic weight masters.

No drawing scaffold, raster tracing, offsetting, interpolation or fitting is
imported here. Missing masters fail closed. Obliques transform their own weight's
control points and anchors without resampling. Font files are never inputs.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
from math import radians, tan, isfinite
from pathlib import Path
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path

UPM=1000
WEIGHTS={100:'Thin',300:'Light',400:'Regular',500:'Medium',600:'Semibold',700:'Bold',800:'Extrabold',900:'Black'}
MASTER_ROOT=Path(__file__).resolve().parents[1]/'sources'/'masters'

class Outline:
    def __init__(self, path: str, shear: float=0):
        self.recording=RecordingPen()
        target=TransformPen(self.recording,(1,0,shear,1,0,0)) if shear else self.recording
        parse_path(path,target)
        if any(op=='endPath' for op,_ in self.recording.value):
            raise ValueError('Open font contour')
        bounds=BoundsPen(None);self.recording.replay(bounds)
        self.is_empty=bounds.bounds is None
        self.bounds=bounds.bounds or (0.,0.,0.,0.)
        if not all(isfinite(v) for v in self.bounds):raise ValueError('Non-finite outline')
    def draw(self,pen):
        self.recording.replay(pen)

@dataclass
class Glyph:
    name: str
    geometry: Outline
    advance: int
    unicodes: list[int]
    base: str | None
    anchor_top: tuple | None
    anchor_bottom: tuple | None
    mark_class: str | None

class Designer:
    def __init__(self,family='zayJu',weight=400,oblique=False,*,source_root=MASTER_ROOT):
        if family not in ('LihuiT','zayJu') or weight not in WEIGHTS:
            raise ValueError('Unsupported family or weight')
        path=Path(source_root)/family/f'{weight}.json'
        data=json.loads(path.read_text(encoding='utf-8'))
        if (data.get('schema'),data.get('family'),data.get('weight'),data.get('upm')) != (1,family,weight,UPM):
            raise ValueError(f'Incorrect master identity: {path}')
        self.family=family;self.weight=weight;self.oblique=oblique
        self.text=family=='LihuiT';self.shear=tan(radians(10)) if oblique else 0
        for name in ('t','h','cap','asc','desc','sb'):
            value=data['metrics'][name]
            if not isinstance(value,(int,float)) or not isfinite(value):raise ValueError('Invalid metric '+name)
            setattr(self,name,value)
        self.alt_maps=data['alt_maps'];self.mark_info=data['mark_info']
        self.glyphs={};self.raw={};self.cmap={}
        for entry in data['glyphs']:
            name=entry['name']
            if name in self.glyphs:raise ValueError('Duplicate glyph '+name)
            raw=Outline(entry['path']);geometry=Outline(entry['path'],self.shear) if oblique else raw
            advance=entry['advance']
            if not isinstance(advance,int) or not 0<=advance<=65535:raise ValueError('Invalid advance '+name)
            top=entry['anchor_top'];bottom=entry['anchor_bottom']
            for anchor in (top,bottom):
                if anchor is not None and (len(anchor)!=2 or not all(isinstance(v,(int,float)) and isfinite(v) for v in anchor)):
                    raise ValueError('Invalid anchor '+name)
            self.raw[name]=(raw,advance,top,bottom)
            self.glyphs[name]=Glyph(name,geometry,advance,entry['unicodes'],entry['base'],self.point(top),self.point(bottom),entry['mark_class'])
            for cp in entry['unicodes']:
                if not isinstance(cp,int) or not 0<=cp<=0x10FFFF or 0xD800<=cp<=0xDFFF:
                    raise ValueError('Invalid Unicode scalar')
                if cp in self.cmap:raise ValueError('Duplicate cmap entry')
                self.cmap[cp]=name
        if len(self.glyphs)!=data['glyph_count'] or len(self.cmap)!=data['codepoint_count']:
            raise ValueError('Incomplete master inventory')
        if not all(cp in self.cmap for cp in range(32,127)):
            raise ValueError('Master lacks printable ASCII')
        self.source_path=path
    def point(self,p):
        return None if p is None else (p[0]+self.shear*p[1],p[1])
    def build(self):
        return self

def draw_geometry(geometry,pen):
    geometry.draw(pen)
