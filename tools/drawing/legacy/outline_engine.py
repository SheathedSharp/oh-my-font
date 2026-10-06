"""LihuiT + zayJu: original, parameterized outline construction.

No system, commercial, or open-source font file is read by this module.
Coordinates are in a 1000 UPM, y-up design space. Cubic design curves are
sampled for boolean operations; the final outline is simplified at 0.10 UPM.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from functools import lru_cache
from math import cos, sin, pi, tan, radians
import unicodedata as ud
from typing import Iterable
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, Point, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely import affinity

UPM = 1000
WEIGHTS = {100:'Thin', 300:'Light', 400:'Regular', 500:'Medium', 600:'Semibold',
           700:'Bold', 800:'Extrabold', 900:'Black'}
STROKES = {'LihuiT': {100:23,300:44,400:66,500:82,600:99,700:116,800:136,900:154},
           'zayJu':{100:22,300:43,400:69,500:88,600:108,700:130,800:151,900:174}}
EMPTY = GeometryCollection()

class Curve:
    def __init__(self, x: float, y: float):
        self.points = [(float(x), float(y))]
    def L(self, x, y):
        self.points.append((float(x), float(y))); return self
    def C(self, x1,y1,x2,y2,x3,y3, steps=24):
        x0,y0=self.points[-1]
        for i in range(1,steps+1):
            t=i/steps; s=1-t
            self.points.append((s*s*s*x0+3*s*s*t*x1+3*s*t*t*x2+t*t*t*x3,
                                s*s*s*y0+3*s*s*t*y1+3*s*t*t*y2+t*t*t*y3))
        return self
    def Q(self, x1,y1,x2,y2):
        x0,y0=self.points[-1]
        return self.C(x0+(x1-x0)*2/3,y0+(y1-y0)*2/3,
                      x2+(x1-x2)*2/3,y2+(y1-y2)*2/3,x2,y2)
    def poly(self):
        return Polygon(self.points).buffer(0)
    def stroke(self, t, cap=2):
        return LineString(self.points).buffer(t/2,cap_style=cap,join_style=1,quad_segs=16)

def rect(x0,y0,x1,y1):
    return box(min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1))
def poly(pts): return Polygon(pts).buffer(0)
def line(pts,t,cap=2): return LineString(pts).buffer(t/2,cap_style=cap,join_style=1,quad_segs=16)
def merge(*gs):
    return unary_union([g for g in gs if g is not None and not g.is_empty]).buffer(0)
def move(g,x=0,y=0): return affinity.translate(g,xoff=x,yoff=y)
def scale(g,x=1,y=None): return affinity.scale(g,xfact=x,yfact=x if y is None else y,origin=(0,0))
def rr(x0,y0,x1,y1,r,k=.60):
    r=max(.2,min(r,(x1-x0)/2,(y1-y0)/2)); d=r*k
    p=Curve(x0+r,y0).L(x1-r,y0)
    p.C(x1-r+d,y0,x1,y0+r-d,x1,y0+r).L(x1,y1-r)
    p.C(x1,y1-r+d,x1-r+d,y1,x1-r,y1).L(x0+r,y1)
    p.C(x0+r-d,y1,x0,y1-r+d,x0,y1-r).L(x0,y0+r)
    p.C(x0,y0+r-d,x0+r-d,y0,x0+r,y0)
    return p.poly()
def ellipse(x0,y0,x1,y1):
    return affinity.scale(Point((x0+x1)/2,(y0+y1)/2).buffer(1,quad_segs=48),
                          xfact=(x1-x0)/2,yfact=(y1-y0)/2,origin=((x0+x1)/2,(y0+y1)/2))
def ring(x0,y0,x1,y1,r,t,k=.60):
    out=rr(x0,y0,x1,y1,r,k)
    if x1-x0 <= 2*t+2 or y1-y0 <= 2*t+2: return out
    return out.difference(rr(x0+t,y0+t,x1-t,y1-t,max(8,r-t*.74),k))

def clean(g):
    if g.is_empty:return EMPTY
    return g.buffer(0).simplify(.10,preserve_topology=True)

@dataclass
class Glyph:
    name: str
    geometry: object
    advance: int
    unicodes: list[int] = field(default_factory=list)
    base: str | None = None
    anchor_top: tuple[float,float] | None = None
    anchor_bottom: tuple[float,float] | None = None
    mark_class: str | None = None

class Designer:
    def __init__(self,family='zayJu',weight=400,oblique=False):
        if family not in STROKES or weight not in WEIGHTS: raise ValueError('Unsupported family or weight')
        self.family=family; self.weight=weight; self.t=STROKES[family][weight]
        self.text=family=='LihuiT'; self.h=548 if self.text else 530
        self.cap=728; self.asc=748; self.desc=-210
        self.r=142 if self.text else 108
        self.k=.57 if self.text else .66
        self.sb=60 if self.text else 42
        self.shear=tan(radians(10)) if oblique else 0
        self.oblique=oblique
        self.glyphs={}; self.cmap={}; self.raw={}
        self.mark_info={}
    def finish(self,g):
        if self.shear:g=affinity.affine_transform(g,[1,self.shear,0,1,0,0])
        return clean(g)
    def point(self,p):
        if p is None:return None
        return (p[0]+self.shear*p[1],p[1])
    def add(self,name,g,advance,cp=None,base=None,top=None,bottom=None,mark_class=None):
        gl=Glyph(name,self.finish(g),round(advance),[] if cp is None else [cp],base,
                 self.point(top),self.point(bottom),mark_class)
        self.glyphs[name]=gl
        self.raw[name]=(g,advance,top,bottom)
        if cp is not None:self.cmap[cp]=name
        return name
    def add_char(self,c,g,w,base=None,sb=None):
        sb=self.sb if sb is None else sb
        name=gname(ord(c)); adv=round(w+2*sb)
        geom=move(g,sb,0)
        ymax=geom.bounds[3] if not geom.is_empty else self.h
        ybottom=geom.bounds[1] if not geom.is_empty else 0
        self.add(name,geom,adv,ord(c),base or c,(adv/2,ymax+55),(adv/2,ybottom-44))
        return name
    def bowl(self,w=490,h=None,t=None,y=0,r=None):
        h=self.h if h is None else h; t=self.t if t is None else t
        return ring(0,y,w,h+y,self.r if r is None else r,t,self.k)
    def spiral_a(self,w=490):
        h=self.h;t=self.t;r=min(self.r,w*.29,h*.28)
        # A continuous open spiral: roof -> right wall -> lower bowl -> diagonal tongue.
        mid=h*.57; br=min(r,mid*.43); ir=max(13,br-t*.48)
        tongue=w*(.66 if self.text else .68)
        p=Curve(w*.23,h).L(w-r,h)
        p.C(w-r*.30,h,w,h-r*.30,w,h-r).L(w,br)
        p.C(w,br*.30,w-br*.30,0,w-br,0).L(br,0)
        p.C(br*.30,0,0,br*.30,0,br).L(0,mid-br)
        p.C(0,mid-br*.30,br*.30,mid,br,mid).L(tongue,mid)
        p.L(tongue-t*.70,mid-t).L(t+ir,mid-t)
        p.C(t+ir*.30,mid-t,t,mid-t-ir*.30,t,mid-t-ir)
        p.L(t,t+ir)
        p.C(t,t+ir*.30,t+ir*.30,t,t+ir,t).L(w-t-ir,t)
        p.C(w-t-ir*.30,t,w-t,t+ir*.30,w-t,t+ir)
        p.L(w-t,h-t-ir)
        p.C(w-t,h-t-ir*.30,w-t-ir*.30,h-t,w-t-ir,h-t)
        p.L(w*.10,h-t).L(w*.23,h)
        return p.poly()
    def desc_hook(self,w=490):
        t=self.t; h=self.h; r=max(78,self.r*.80); d=self.desc
        p=Curve(w-t/2,h).L(w-t/2,d+r)
        p.C(w-t/2,d+t/2,w-r,d+t/2,w-r-t*.1,d+t/2).L(40+t*.30,d+t/2)
        g=p.stroke(t)
        # A clean diagonal lower terminal, echoing the roof of a.
        cutter=poly([(-200,d-100),(45,d-100),(45+t*.65,d+t),(0,d+t),(-200,d+t)])
        return g.difference(cutter)
    def u_shape(self,w=490,h=None):
        h=self.h if h is None else h;t=self.t;r=max(self.r,t*.80)
        return Curve(t/2,h).L(t/2,r).C(t/2,t/2,r*.7,t/2,r,t/2).L(w-r,t/2).C(w-r*.65,t/2,w-t/2,t/2,w-t/2,r).L(w-t/2,h).stroke(t)
    def n_shape(self,w=490,h=None):
        h=self.h if h is None else h;t=self.t;r=max(self.r,t*.8)
        return Curve(t/2,0).L(t/2,h-r).C(t/2,h-t/2,r*.7,h-t/2,r,h-t/2).L(w-r,h-t/2).C(w-r*.65,h-t/2,w-t/2,h-t/2,w-t/2,h-r).L(w-t/2,0).stroke(t)
    def c_shape(self,w=490,h=None):
        h=self.h if h is None else h;t=self.t
        r=max(self.r,t*.84)
        return Curve(w-12,h-t/2).L(r,h-t/2).C(t/2,h-t/2,t/2,h-r,t/2,h-r).L(t/2,r).C(t/2,t/2,r,t/2,r,t/2).L(w-12,t/2).stroke(t)
    def s_shape(self,w=485,h=None):
        h=self.h if h is None else h;t=self.t
        r=min(self.r,h*.28); mid=h*.51
        return Curve(w-10,h-t/2).L(r,h-t/2).C(t/2,h-t/2,t/2,h-r,t/2,h-r).L(t/2,mid+r*.35).C(t/2,mid,w*.32,mid,w*.50,mid).L(w-r,mid).C(w-t/2,mid,w-t/2,mid-r*.35,w-t/2,mid-r*.68).L(w-t/2,r).C(w-t/2,t/2,w-r,t/2,w-r,t/2).L(8,t/2).stroke(t)
    def z_shape(self,w=500,h=None):
        h=self.h if h is None else h;t=self.t
        # Horizontal terminals and a single strong diagonal, no ornamental slash.
        g=poly([(0,h),(w,h),(w,h-t),(t*1.40,t),(w,t),(w,0),(0,0),(0,t),(w-t*1.40,h-t),(0,h-t)])
        # Subtle rounding at the two turning points, without stroke-union notches.
        rad=min(7,t*.12)
        return g.buffer(-rad,quad_segs=8).buffer(rad,quad_segs=8)
    def upper(self,c):
        t=self.t;h=self.cap;w=555;r=self.r+24;k=self.k
        if c=='A':
            w=605;g=merge(line([(t*.47,0),(w/2,h-t*.38),(w-t*.47,0)],t),rect(w*.22,h*.35,w*.78,h*.35+t*.88))
        elif c=='B':
            w=550; split=h*.52
            g=merge(ring(0,split-t*.45,w-24,h,r,t,k),ring(0,0,w,split+t*.42,r,t,k),rect(0,0,t,h))
        elif c=='C': g=self.c_shape(w,h)
        elif c=='D': g=merge(ring(0,0,w,h,r*1.32,t,k),rect(0,0,t,h))
        elif c=='E': w=490;g=merge(rect(0,0,t,h),rect(0,h-t,w,h),rect(0,h*.49,w*.84,h*.49+t*.92),rect(0,0,w,t))
        elif c=='F': w=478;g=merge(rect(0,0,t,h),rect(0,h-t,w,h),rect(0,h*.49,w*.85,h*.49+t*.92))
        elif c=='G':
            w=578;g=merge(self.c_shape(w,h),rect(w-t,h*.05,w,h*.47),rect(w*.51,h*.47-t,w,h*.47))
        elif c=='H':g=merge(rect(0,0,t,h),rect(w-t,0,w,h),rect(0,h*.48,w,h*.48+t*.94))
        elif c=='I':w=320;g=merge(rect((w-t)/2,0,(w+t)/2,h),rect(0,0,w,t*.85),rect(0,h-t*.85,w,h))
        elif c=='J':
            w=438;g=Curve(w-t/2,h).L(w-t/2,r).C(w-t/2,t/2,w-r,t/2,w-r,t/2).L(r,t/2).C(t/2,t/2,t/2,r,t/2,r).L(t/2,h*.26).stroke(t)
        elif c=='K':
            w=565;g=merge(rect(0,0,t,h),line([(w-t*.28,h),(t*.65,h*.43)],t*.94),line([(w*.40,h*.51),(w-t*.30,0)],t*.98))
        elif c=='L': w=475;g=merge(rect(0,0,t,h),rect(0,0,w,t))
        elif c=='M':
            w=720;g=merge(rect(0,0,t,h),rect(w-t,0,w,h),line([(t*.55,h-t*.38),(w/2,h*.32),(w-t*.55,h-t*.38)],t*.93))
        elif c=='N':
            w=580;g=merge(rect(0,0,t,h),rect(w-t,0,w,h),line([(t*.60,h-t*.4),(w-t*.60,t*.4)],t*.95))
        elif c=='O':
            w=590;g=ring(0,-7,w,h+7,r*1.50,t,k)
        elif c=='P':
            w=535;g=merge(ring(0,h*.40,w,h,r,t,k),rect(0,0,t,h))
        elif c=='Q':
            w=590;g=merge(ring(0,-7,w,h+7,r*1.5,t,k),line([(w*.57,h*.23),(w+12,-65)],t*.80))
        elif c=='R':
            w=565;g=merge(ring(0,h*.42,w-18,h,r,t,k),rect(0,0,t,h),line([(w*.48,h*.45),(w-t*.25,0)],t*.95))
        elif c=='S': w=535;g=self.s_shape(w,h)
        elif c=='T': w=560;g=merge(rect(0,h-t,w,h),rect((w-t)/2,0,(w+t)/2,h))
        elif c=='U': w=565;g=self.u_shape(w,h)
        elif c=='V':
            w=600;g=line([(t*.46,h),(w/2,t*.4),(w-t*.46,h)],t)
        elif c=='W':
            w=845;g=line([(t*.5,h),(w*.235,t*.5),(w*.50,h*.70),(w*.765,t*.5),(w-t*.5,h)],t*.95)
        elif c=='X': w=580;g=merge(line([(t*.4,0),(w-t*.4,h)],t*.94),line([(t*.4,h),(w-t*.4,0)],t*.94))
        elif c=='Y':
            w=590;g=merge(line([(t*.4,h),(w/2,h*.42),(w-t*.4,h)],t*.97),rect((w-t)/2,0,(w+t)/2,h*.46))
        elif c=='Z': w=565;g=self.z_shape(w,h)
        else:raise KeyError(c)
        return clean(g),w
    def lower(self,c):
        t=self.t;h=self.h;w=490;r=self.r
        if c=='a':g=self.spiral_a(w)
        elif c=='b': g=merge(self.bowl(w),rect(0,0,t,self.asc))
        elif c=='c':g=self.c_shape(w)
        elif c=='d':g=merge(self.bowl(w),rect(w-t,0,w,self.asc))
        elif c=='e':
            # Open right aperture: upper counter remains a closed rounded rectangle.
            et=min(t,h*.21);egap=h*.34
            g=merge(self.c_shape(w),ring(0,egap,w,h,r,et,self.k),rect(0,egap,w*.88,egap+et))
        elif c=='f':
            w=345;g=merge(Curve(t/2,0).L(t/2,self.asc-r).C(t/2,self.asc-t/2,r,self.asc-t/2,r,self.asc-t/2).L(w,self.asc-t/2).stroke(t),rect(0,h*.64,w*.92,h*.64+t*.92));
        elif c=='g':g=merge(self.bowl(w),self.desc_hook(w))
        elif c=='h':g=merge(self.n_shape(w),rect(0,0,t,self.asc))
        elif c=='i':
            w=t;dot=max(t,68 if self.text else 62);g=merge(rect(0,0,t,h),rr((t-dot)/2,h+94,(t+dot)/2,h+94+dot,dot*.20))
        elif c=='j':
            w=236;dot=max(t,68 if self.text else 62)
            g=merge(Curve(w-t/2,h).L(w-t/2,self.desc+95).C(w-t/2,self.desc+t/2,w-120,self.desc+t/2,w-120,self.desc+t/2).L(0,self.desc+t/2).stroke(t),rr(w-t/2-dot/2,h+94,w-t/2+dot/2,h+94+dot,dot*.20))
        elif c=='k':
            w=458;g=merge(rect(0,0,t,self.asc),line([(w-t*.25,h),(t*.60,h*.39)],t*.92),line([(w*.42,h*.50),(w-t*.3,0)],t*.95))
        elif c=='l':
            w=t+105;g=Curve(t/2,self.asc).L(t/2,104).C(t/2,t/2,100,t/2,108,t/2).L(w,t/2).stroke(t)
        elif c=='m':
            w=750;half=(w+t)/2;g=merge(self.n_shape(half),move(self.n_shape(half),half-t))
        elif c=='n':g=self.n_shape(w)
        elif c=='o':g=ring(0,-7,w,h+7,r*1.18,t,self.k)
        elif c=='p':g=merge(self.bowl(w),rect(0,self.desc,t,h))
        elif c=='q':g=merge(self.bowl(w),rect(w-t,self.desc,w,h))
        elif c=='r':
            w=324;g=Curve(t/2,0).L(t/2,h-r).C(t/2,h-t/2,r,h-t/2,r,h-t/2).L(w,h-t/2).stroke(t)
        elif c=='s':w=462;g=self.s_shape(w,h)
        elif c=='t':
            w=354;g=merge(Curve(t/2,h+155).L(t/2,r).C(t/2,t/2,r,t/2,r,t/2).L(w,t/2).stroke(t),rect(-62,h*.72,w*.93,h*.72+t*.93))
        elif c=='u':g=self.u_shape(w)
        elif c=='v':w=510;g=line([(t*.43,h),(w/2,t*.4),(w-t*.43,h)],t*.96)
        elif c=='w':
            w=713;g=line([(t*.47,h),(w*.235,t*.44),(w*.5,h*.74),(w*.765,t*.44),(w-t*.47,h)],t*.92)
        elif c=='x':w=500;g=merge(line([(t*.40,0),(w-t*.40,h)],t*.93),line([(t*.40,h),(w-t*.40,0)],t*.93))
        elif c=='y':g=merge(self.u_shape(w),self.desc_hook(w))
        elif c=='z':w=472;g=self.z_shape(w,h)
        else:raise KeyError(c)
        # The body cut has slightly more breathing room around junctions.
        return clean(g),w
    def digit(self,d):
        t=self.t;h=self.cap*.94;w=500;r=self.r*1.12
        if d=='0':g=ring(0,-5,w,h+5,r,t,self.k)
        elif d=='1':
            w=340;x=w*.58;g=merge(rect(x-t/2,0,x+t/2,h),line([(24,h*.75),(x,h-t*.38)],t*.91),rect(22,0,w,t*.82))
        elif d=='2':
            g=Curve(t/2,h-r).C(t/2,h-t/2,r,h-t/2,r,h-t/2).L(w-r,h-t/2).C(w-t/2,h-t/2,w-t/2,h-r,w-t/2,h-r).L(w-t/2,h*.60).C(w-t/2,h*.49,w*.66,h*.44,w*.50,h*.36).L(t/2,t*.56).L(w,t/2).stroke(t)
        elif d=='3':
            g=merge(Curve(8,h-t/2).L(w-r,h-t/2).C(w-t/2,h-t/2,w-t/2,h-r,w-t/2,h-r).L(w-t/2,h*.64).C(w-t/2,h*.51,w-r,h*.50,w-r,h*.50).L(w*.25,h*.50).stroke(t),Curve(w-r,h*.50).C(w-t/2,h*.50,w-t/2,h*.39,w-t/2,h*.34).L(w-t/2,r).C(w-t/2,t/2,w-r,t/2,w-r,t/2).L(8,t/2).stroke(t))
        elif d=='4':
            g=merge(rect(w*.69-t/2,0,w*.69+t/2,h),line([(t*.55,h),(t*.55,h*.37),(w,h*.37)],t))
        elif d=='5':
            g=merge(rect(0,h-t,w,h),rect(0,h*.50,t,h),Curve(t/2,h*.51).L(w-r,h*.51).C(w-t/2,h*.51,w-t/2,h*.37,w-t/2,h*.34).L(w-t/2,r).C(w-t/2,t/2,w-r,t/2,w-r,t/2).L(0,t/2).stroke(t))
        elif d=='6':
            g=merge(ring(0,0,w,h*.60,r,t,self.k),Curve(t/2,h*.26).L(t/2,h-r).C(t/2,h-t/2,r,h-t/2,r,h-t/2).L(w-10,h-t/2).stroke(t))
        elif d=='7':g=merge(rect(0,h-t,w,h),line([(w-t*.50,h-t*.40),(w*.31,0)],t*.98))
        elif d=='8':g=merge(ring(0,h*.49,w,h,r,t,self.k),ring(0,0,w,h*.53,r,t,self.k))
        elif d=='9':
            g=merge(ring(0,h*.40,w,h,r,t,self.k),Curve(w-t/2,h*.71).L(w-t/2,r).C(w-t/2,t/2,w-r,t/2,w-r,t/2).L(8,t/2).stroke(t))
        else:raise KeyError(d)
        return clean(g),w
    def make_basic(self):
        t=self.t
        self.add('.notdef',ring(60,0,530,728,20,max(25,t*.60)),590)
        self.add('.null',EMPTY,0,0)
        self.add('nonmarkingreturn',EMPTY,0,13)
        for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            g,w=self.upper(c);self.add_char(c,g,w)
        for c in 'abcdefghijklmnopqrstuvwxyz':
            g,w=self.lower(c)
            # t crossbar has a left overhang: preserve a genuine left sidebearing.
            if c=='t': g=move(g,62);w+=62
            side=self.sb+(12 if c in 'ijl' else 0)
            self.add_char(c,g,w,sb=side)
        for d in '0123456789':
            g,w=self.digit(d);self.add_char(d,g,w)
        for cp,adv in [(32,290 if self.text else 252),(160,290 if self.text else 252),(0x2000,500),(0x2001,1000),(0x2002,500),(0x2003,1000),(0x2004,333),(0x2005,250),(0x2006,167),(0x2007,620),(0x2008,250),(0x2009,190),(0x200A,95),(0x200B,0),(0x202F,190),(0x2060,0),(0xFEFF,0)]:
            self.add(gname(cp),EMPTY,adv,cp)

    def symbol(self,c):
        t=self.t;st=max(24,t*.74);h=self.h;cap=self.cap;mid=cap*.44;w=500
        dot=max(62,t); dotg=rr(0,0,dot,dot,dot*.20)
        if c=='.':return dotg,dot
        if c==',':return merge(dotg,line([(dot*.67,22),(dot*.25,-100)],max(23,dot*.37))),dot
        if c==':':return merge(dotg,move(dotg,0,h*.61)),dot
        if c==';':g,w=self.symbol(',');return merge(g,move(dotg,0,h*.61)),dot
        if c in "'\"":
            g=rect(0,cap-150,st,cap);return (merge(g,move(g,st+64)) if c=='"' else g), (2*st+64 if c=='"' else st)
        if c in '‘’‚“”„':
            down=c in '‚„';left=c in '‘“'
            y=0 if down else cap-115
            sg=merge(rr(0,y,st,y+90,st*.15),line([(st*.28,y+65 if left else y+15),(st*.65,y+160 if left else y-80)],st*.62))
            double=c in '“”„';return (merge(sg,move(sg,st+64)) if double else sg),(2*st+64 if double else st)
        if c in '-‐‑–—−':
            w={'-':315,'‐':315,'‑':315,'–':520,'—':860,'−':510}[c];return rect(0,mid-st/2,w,mid+st/2),w
        if c=='_':return rect(0,-123,545,-123+st),545
        if c in '/\\':
            w=395;g=line([(0,-65),(w,cap+40)] if c=='/' else [(0,cap+40),(w,-65)],st);return g,w
        if c=='|':return rect(0,-120,st,cap+70),st
        if c=='¦':return merge(rect(0,-120,st,230),rect(0,365,st,cap+70)),st
        if c in '()[]{}':
            w=260;top=cap+70;bot=-145
            if c in '()':g=Curve(w*.80,top).C(-20,top-130,-20,bot+130,w*.80,bot).stroke(st)
            elif c in '[]':g=line([(w,top),(st/2,top),(st/2,bot),(w,bot)],st)
            else:g=Curve(w,top).L(w*.6,top).C(w*.2,top,w*.6,mid+80,0,mid).C(w*.6,mid-80,w*.2,bot,w*.6,bot).L(w,bot).stroke(st)
            if c in ')]}':g=move(scale(g,-1,1),w)
            return g,w
        if c=='+':return merge(rect(0,mid-st/2,w,mid+st/2),rect(w/2-st/2,mid-250,w/2+st/2,mid+250)),w
        if c=='=':return merge(rect(0,mid+85,w,mid+85+st),rect(0,mid-100-st,w,mid-100)),w
        if c=='×':return merge(line([(45,mid-205),(455,mid+205)],st),line([(45,mid+205),(455,mid-205)],st)),w
        if c=='÷':return merge(rect(0,mid-st/2,w,mid+st/2),move(dotg,(w-dot)/2,mid+140),move(dotg,(w-dot)/2,mid-140-dot)),w
        if c in '<>':
            g=line([(w,mid+230),(0,mid),(w,mid-230)],st)
            if c=='>':g=move(scale(g,-1,1),w)
            return g,w
        if c in '≤≥':
            g,_=self.symbol('<' if c=='≤' else '>');g=move(scale(g,1,.78),0,95)
            return merge(g,rect(0,25,w,25+st)),w
        if c=='≠':g,_=self.symbol('=');return merge(g,line([(140,mid-235),(365,mid+255)],st)),w
        if c=='±':g,_=self.symbol('+');return merge(move(scale(g,1,.74),0,135),rect(0,-20,w,-20+st)),w
        if c in '~≈':
            g=Curve(0,mid).C(180,mid+165,310,mid-165,w,mid).stroke(st)
            if c=='≈':g=merge(move(g,0,105),move(g,0,-105))
            return g,w
        if c=='^':return line([(15,cap-200),(w/2,cap),(w-15,cap-200)],st),w
        if c=='`':return line([(35,cap+15),(165,cap-115)],st),190
        if c=='!':return merge(rect(0,190,t,cap),rr(0,0,t,t,t*.2)),t
        if c=='?':
            w=440;r=100;g=Curve(t/2,cap-170).C(t/2,cap-t/2,r,cap-t/2,r,cap-t/2).L(w-r,cap-t/2).C(w-t/2,cap-t/2,w-t/2,cap-r,w-t/2,cap-r).L(w-t/2,cap*.65).C(w-t/2,cap*.51,w*.51,cap*.50,w*.51,cap*.36).L(w*.51,190).stroke(t)
            return merge(g,rr(w*.51-t/2,0,w*.51+t/2,t,t*.2)),w
        if c=='#':
            return merge(line([(125,0),(230,cap)],st),line([(335,0),(440,cap)],st),rect(0,cap*.33,w+52,cap*.33+st),rect(30,cap*.65,w+70,cap*.65+st)),w+70
        if c=='*':
            w=390;return merge(*(line([(w/2,cap-190),(w/2+182*cos(a),cap-190+182*sin(a))],st) for a in [pi/2,pi/2+2*pi/5,pi/2+4*pi/5,pi/2+6*pi/5,pi/2+8*pi/5])),w
        if c in '%‰':
            w=580 if c=='%' else 880;sz=225
            rg=ring(0,0,sz,sz,90,max(22,t*.53),.57)
            gs=[move(rg,0,cap-sz),move(rg,335,0),line([(85,0),(485,cap)],st)]
            if c=='‰':gs.append(move(rg,635,0))
            return merge(*gs),w
        if c=='&':
            w=585
            g=Curve(w-12,10).L(w*.21,cap*.67).C(-25,cap+45,w*.76,cap+75,w*.68,cap*.73).C(w*.66,cap*.61,t/2,cap*.41,t/2,cap*.25).C(t/2,-30,w*.74,-80,w-22,cap*.43).stroke(t*.90)
            return g,w
        if c=='@':
            w=780;outer=Curve(w*.73,92).C(w*.20,-105,-25,50,t/2,cap*.48).C(t/2,cap+175,w,cap+140,w-t/2,cap*.45).L(w-t/2,cap*.32).C(w-t/2,cap*.14,w*.70,cap*.13,w*.70,cap*.30).L(w*.70,cap*.71).stroke(st)
            return merge(outer,ring(w*.28,cap*.22,w*.70,cap*.73,110,st,.58)),w
        if c in '$¢€£¥₹₿₩₽₺₴':
            if c=='$':g,w=self.upper('S');return merge(g,rect(w*.48-st*.25,-80,w*.48+st*.25,cap+80)),w
            if c=='¢':g,w=self.lower('c');return merge(g,rect(w*.49-st*.25,-90,w*.49+st*.25,h+90)),w
            if c=='€':g,w=self.upper('C');return merge(g,rect(-35,cap*.40,w*.77,cap*.40+st*.68),rect(-35,cap*.57,w*.85,cap*.57+st*.68)),w
            if c=='£':
                g,w=self.lower('f');g=scale(g,1,cap/self.asc);return merge(g,rect(-30,0,470,t),rect(-28,cap*.44,320,cap*.44+st)),470
            if c=='¥':g,w=self.upper('Y');return merge(g,rect(80,cap*.27,w-80,cap*.27+st*.67),rect(80,cap*.43,w-80,cap*.43+st*.67)),w
            if c=='₹':
                g,w=self.upper('R');g=g.difference(rect(0,0,t+1,cap*.51));return merge(g,rect(-35,cap-st,w,cap),rect(-35,cap*.72,w,cap*.72+st)),w
            if c=='₿':g,w=self.upper('B');return merge(g,rect(130,-75,130+st*.65,cap+75),rect(295,-75,295+st*.65,cap+75)),w
            if c=='₩':g,w=self.upper('W');return merge(g,rect(-10,cap*.43,w+10,cap*.43+st*.65),rect(-10,cap*.59,w+10,cap*.59+st*.65)),w
            if c=='₽':g,w=self.upper('P');return merge(g,rect(-40,cap*.26,w*.75,cap*.26+st*.8)),w
            if c=='₺':g,w=self.upper('L');return merge(g,line([(-45,cap*.35),(w*.77,cap*.58)],st*.74),line([(-45,cap*.53),(w*.77,cap*.76)],st*.74)),w
            if c=='₴':g,w=self.upper('S');return merge(g,rect(-10,cap*.42,w+10,cap*.42+st*.7),rect(-10,cap*.57,w+10,cap*.57+st*.7)),w
        if c=='°':return ring(0,cap-240,240,cap,115,max(26,t*.58),.56),240
        if c in '©®':
            w=800;out=ellipse(0,-30,w,770).difference(ellipse(st,-30+st,w-st,770-st));g,gw=self.upper('C' if c=='©' else 'R');g=move(scale(g,.49), (w-gw*.49)/2,190);return merge(out,g),w
        if c=='™':
            g1,w1=self.upper('T');g2,w2=self.upper('M');return merge(move(scale(g1,.40),0,cap*.60),move(scale(g2,.40),w1*.4+30,cap*.60)),(w1+w2)*.4+30
        if c=='¶':
            w=470;g=merge(ring(0,cap*.43,w*.84,cap,155,t,self.k),rect(w*.48,-95,w*.48+t,cap),rect(w-t,-95,w,cap));return g,w
        if c=='§':
            g,w=self.upper('S');return merge(move(scale(g,1,.68),0,cap*.39),move(scale(g,1,.68),0,-65)),w
        if c in '†‡':
            w=370;g=merge(rect(w/2-st/2,-120,w/2+st/2,cap),rect(0,cap*.60,w,cap*.60+st))
            if c=='‡':g=merge(g,rect(0,cap*.20,w,cap*.20+st))
            return g,w
        if c in '·•':
            d=80 if c=='·' else 155;return ellipse(0,mid-d/2,d,mid+d/2),d
        if c=='…':return merge(dotg,move(dotg,dot+125),move(dotg,2*(dot+125))),3*dot+250
        if c in '«»‹›':
            g,w1=self.symbol('<' if c in '«‹' else '>');g=move(scale(g,.48,.65),0,85);double=c in '«»'
            return (merge(g,move(g,230)) if double else g),(470 if double else 240)
        if c in '¬':return line([(0,mid+90),(w,mid+90),(w,mid-115)],st),w
        if c in '∧∨':
            return line([(0,mid-205 if c=='∧' else mid+205),(w/2,mid+205 if c=='∧' else mid-205),(w,mid-205 if c=='∧' else mid+205)],st),w
        if c in '∑Σ':return line([(560,cap),(30,cap),(340,mid),(30,0),(560,0)],st),580
        if c in '∏Π':return merge(rect(0,cap-st,600,cap),rect(80,0,80+st,cap),rect(520-st,0,520,cap)),600
        if c in '∆Δ':return merge(line([(20,st/2),(300,cap-st/2),(580,st/2),(20,st/2)],st)),600
        if c=='π':return merge(rect(0,h-st,560,h),rect(95,0,95+st,h),rect(425-st,0,425,h)),560
        if c=='Ω':
            g,w=self.upper('O');g=g.difference(rect(180,-40,w-180,140));return merge(g,rect(-5,0,220,st),rect(w-220,0,w+5,st)),w
        if c in 'µμ':g,w=self.lower('u');return merge(g,rect(0,-200,t,h)),w
        if c=='∂':
            g=merge(ring(0,0,490,h*.75,130,st,self.k),Curve(490-st/2,h*.37).C(600,cap+40,270,cap+90,120,cap*.86).stroke(st));return g,530
        if c=='∞':
            w=720;g=Curve(w/2,mid).C(120,mid+390,-100,mid+80,80,mid-145).C(235,mid-330,510,mid+300,660,mid+145).C(855,mid-65,600,mid-390,w/2,mid).stroke(st);return g,w
        if c in '∅Øø':
            g,w=self.upper('O') if c!='ø' else self.lower('o');hh=cap if c!='ø' else h
            return merge(g,line([(-12,-35),(w+12,hh+35)],st*.80)),w
        if c=='√':return line([(0,mid),(100,mid),(215,0),(405,cap),(700,cap)],st),700
        if c=='∫':return Curve(420,cap+70).C(180,cap+130,335,mid-130,160,-160).C(115,-220,50,-170,20,-130).stroke(st),450
        if c in '←→↑↓↔↕↗↘↙↖⇐⇒⇑⇓⇔⇕':
            # Draw rightward first, rotate around its mathematical center.
            double=c in '⇐⇒⇑⇓⇔⇕';both=c in '↔↕⇔⇕';w=700
            st2=max(22,st*.82)
            shaft=merge(line([(30,mid+52),(650,mid+52)],st2*.72),line([(30,mid-52),(650,mid-52)],st2*.72)) if double else line([(30,mid),(650,mid)],st2)
            g=merge(shaft,line([(445,mid+220),(665,mid),(445,mid-220)],st2))
            if both:g=merge(g,line([(240,mid+220),(20,mid),(240,mid-220)],st2))
            angle={'←':180,'⇐':180,'↑':90,'⇑':90,'↓':-90,'⇓':-90,'↕':90,'⇕':90,'↗':45,'↘':-45,'↙':-135,'↖':135}.get(c,0)
            return affinity.rotate(g,angle,origin=(350,mid)),w
        if c=='↵':return merge(line([(620,650),(620,mid),(70,mid)],st),line([(275,mid+190),(70,mid),(275,mid-190)],st)),670
        if c=='⌘':
            s=230;g=ring(70,mid-230,470,mid+170,45,st,.60)
            return merge(g,*(ring(x,y,x+s,y+s,90,st,.6) for x,y in [(0,mid+60),(310,mid+60),(0,mid-350),(310,mid-350)])),560
        if c=='⌥':return merge(line([(0,cap*.76),(170,cap*.76),(450,40),(650,40)],st),rect(350,cap*.76-st/2,650,cap*.76+st/2)),650
        if c=='⎋':
            g=ellipse(0,0,620,620).difference(ellipse(st,st,620-st,620-st));return merge(g,line([(170,450),(650,-20)],st),line([(650,200),(650,-20),(430,-20)],st)),660
        if c=='□':return ring(0,0,560,560,10,st),560
        if c=='■':return rect(0,0,560,560),560
        if c in '○●':return (ellipse(0,0,560,560) if c=='●' else ellipse(0,0,560,560).difference(ellipse(st,st,560-st,560-st))),560
        if c=='✓':return line([(0,280),(165,80),(540,650)],st),550
        raise KeyError(c)

    def make_symbols(self):
        chars=".,:;'\"‘’‚“”„-‐‑–—−_/\\|¦()[]{}+=×÷<>≤≥≠±~≈^`!?#*%‰&@$¢€£¥₹₿₩₽₺₴°©®™¶§†‡·•…«»‹›¬∧∨∑Σ∏Π∆ΔπΩµμ∂∞∅Øø√∫←→↑↓↔↕↗↘↙↖⇐⇒⇑⇓⇔⇕↵⌘⌥⎋□■○●✓"
        for c in dict.fromkeys(chars):
            g,w=self.symbol(c);sb=max(self.sb,55 if c in '()[]{}' else self.sb)
            # Make every symbol's actual bearings nonnegative, including rotated arrows.
            if not g.is_empty and g.bounds[0]<0:
                dx=-g.bounds[0];g=move(g,dx);w+=dx
            self.add_char(c,g,w,sb=sb)
        # Inverted punctuation is a real rotation rather than a renamed upright glyph.
        for c,base in [('¡','!'),('¿','?')]:
            g,w=self.symbol(base);g=affinity.rotate(g,180,origin=(w/2,self.h/2));self.add_char(c,g,w)
        # Soft hyphen has the hyphen drawing; layout engines determine visibility.
        n=self.cmap[ord('-')];g,a,top,bot=self.raw[n]
        self.add(gname(173),g,a,173,'-',top,bot)

    @lru_cache(maxsize=2048)
    def accent(self,cp):
        t=max(28,self.t*.61);gap=16;w=245
        if cp==0x300:g=line([(-75,140),(70,5)],t)
        elif cp==0x301:g=line([(-70,5),(75,140)],t)
        elif cp==0x302:g=line([(-123,0),(0,122),(123,0)],t)
        elif cp==0x303:g=Curve(-145,40).C(-60,150,60,-65,145,45).stroke(t)
        elif cp==0x304:g=rect(-140,22,140,22+t)
        elif cp==0x306:g=Curve(-140,110).C(-115,-45,115,-45,140,110).stroke(t)
        elif cp==0x307:g=rr(-t*.65,15,t*.65,15+t*1.3,t*.19)
        elif cp==0x308:
            d=max(58,self.t*.60);g=merge(rr(-112,10,-112+d,10+d,d*.2),rr(112-d,10,112,10+d,d*.2))
        elif cp==0x309:g=Curve(-40,10).C(135,80,90,190,-25,150).stroke(t)
        elif cp==0x30A:g=ellipse(-93,0,93,185).difference(ellipse(-93+t,0+t,93-t,185-t))
        elif cp==0x30B:g=merge(line([(-134,0),(-24,142)],t),line([(10,0),(120,142)],t))
        elif cp==0x30C:g=line([(-123,125),(0,0),(123,125)],t)
        elif cp==0x30F:g=merge(line([(-125,142),(-15,0)],t),line([(16,142),(126,0)],t))
        elif cp==0x311:g=Curve(-140,0).C(-115,155,115,155,140,0).stroke(t)
        elif cp==0x31B:g=Curve(-5,-10).C(145,-10,137,118,88,165).stroke(t*.87)
        elif cp==0x323:g=rr(-t*.65,-t*1.3,t*.65,0,t*.2)
        elif cp==0x324:
            d=max(58,self.t*.60);g=merge(rr(-112,-d,-112+d,0,d*.2),rr(112-d,-d,112,0,d*.2))
        elif cp in [0x326,0x327]:g=Curve(25,5).L(-18,-61).C(120,-45,112,-175,-65,-145).stroke(t*.77)
        elif cp==0x328:g=Curve(35,8).C(-145,-130,-10,-178,75,-125).stroke(t*.82)
        elif cp==0x32D:g=line([(-120,-5),(0,-122),(120,-5)],t)
        elif cp==0x32E:g=Curve(-140,-5).C(-115,-160,115,-160,140,-5).stroke(t)
        elif cp in (0x331,0x332):g=rect(-145,-t-10,145,-10)
        elif cp==0x330:g=move(self.accent(0x303),0,-110)
        elif cp==0x335:g=rect(-150,0,150,t)
        elif cp==0x338:g=line([(-210,-280),(210,430)],t)
        else:raise KeyError(cp)
        return clean(g)
    def make_accents(self):
        self.accents=[0x300,0x301,0x302,0x303,0x304,0x306,0x307,0x308,0x309,0x30A,0x30B,0x30C,0x30F,0x311,0x31B,0x323,0x324,0x326,0x327,0x328,0x32D,0x32E,0x330,0x331,0x332,0x335,0x338]
        for cp in self.accents:
            g=self.accent(cp)
            cls='bottom' if ud.combining(chr(cp)) in (202,220) else ('overlay' if cp in [0x335,0x338] else ('horn' if cp==0x31B else 'top'))
            self.add(gname(cp),g,0,cp,mark_class=cls)
            self.mark_info[gname(cp)]={'class':cls,'top':g.bounds[3]+45,'bottom':g.bounds[1]-40}
        for cp,comb in {0xA8:0x308,0xAF:0x304,0xB4:0x301,0xB8:0x327,0x2C6:0x302,0x2C7:0x30C,0x2D8:0x306,0x2D9:0x307,0x2DA:0x30A,0x2DB:0x328,0x2DC:0x303,0x2DD:0x30B}.items():
            g=move(self.accent(comb),180,self.cap-145 if comb!=0x327 and comb!=0x328 else 0)
            self.add(gname(cp),g,360,cp)
        for cp,c in [(0x131,'i'),(0x237,'j')]:
            n=self.cmap[ord(c)];g,a,top,bot=self.raw[n];g=g.difference(rect(-500,self.h+1,1500,1300))
            self.add(gname(cp),g,a,cp,c,(a/2,self.h+55),bot)

    def make_special_latin(self):
        t=self.t
        # Currency sign, eth, middle-dot L, and eng are non-decomposing Latin forms.
        cg=ring(55,160,465,570,175,max(24,t*.70),.58)
        cg=merge(cg,*(line([a,b],max(24,t*.65)) for a,b in [((50,150),(140,240)),((390,490),(485,585)),((50,585),(140,495)),((390,240),(485,145))]))
        self.add_char('¤',cg,530)
        g,w=self.lower('o')
        eth=merge(g,Curve(w-self.t/2,self.h*.40).C(w+12,self.asc-40,w*.47,self.asc+50,w*.19,self.asc-28).stroke(t),line([(w*.31,self.asc-122),(w*.72,self.asc+15)],max(25,t*.65)))
        self.add_char('ð',eth,w,'d')
        for c,base in [('Ŀ','L'),('ŀ','l')]:
            g,w=self.upper(base) if base.isupper() else self.lower(base)
            dot=max(62,t*.75);g=merge(g,rr(w-dot,self.h*.52,w,self.h*.52+dot,dot*.2))
            self.add_char(c,g,w,base)
        for c,base in [('Ŋ','N'),('ŋ','n')]:
            g,w=self.upper(base) if base.isupper() else self.lower(base)
            g=merge(g,self.desc_hook(w));self.add_char(c,g,w,base)
        fg,fw=self.lower('f');fg=merge(fg,Curve(t/2,10).L(t/2,-90).C(t/2,-200,-30,-200,-90,-200).stroke(t))
        self.add_char('ƒ',move(fg,90),fw+90,'f')
        for c,base in [('Ð','D'),('Đ','D'),('đ','d'),('Ħ','H'),('ħ','h'),('Ł','L'),('ł','l'),('Ŧ','T'),('ŧ','t')]:
            g,w=self.upper(base) if base.isupper() else self.lower(base)
            hh=self.cap if base.isupper() else self.h
            if c in 'Łł':bar=line([(-35,hh*.31),(w*.81,hh*.66)],max(25,t*.66))
            else:bar=rect(-45,hh*.52,w*.72,hh*.52+t*.70)
            self.add_char(c,merge(g,bar),w,base)
        for c,stem,loop in [('Þ','I','P'),('þ','l','p')]:
            if c=='Þ':g,w=self.upper('P');g=move(scale(g,1,.70),0,92);g=merge(g,rect(0,0,t,self.cap))
            else:g,w=self.lower('p');g=merge(g,rect(0,self.desc,t,self.asc))
            self.add_char(c,g,w,'P' if c=='Þ' else 'p')
        # Real paired-letter forms for AE/OE, not Unicode aliases.
        for c,a,b in [('Æ','A','E'),('æ','a','e'),('Œ','O','E'),('œ','o','e')]:
            f=self.upper if a.isupper() else self.lower
            g1,w1=f(a);g2,w2=f(b);xf=.79;join=32 if self.text else 42
            g=merge(scale(g1,xf,1),move(scale(g2,xf,1),w1*xf-join))
            self.add_char(c,g,(w1+w2)*xf-join,a)
        # Sharp-s: ascender and open upper lobe, clearly distinct from capital B.
        w=495;h=self.asc
        g=Curve(self.t/2,0).L(self.t/2,h-120).C(self.t/2,h-self.t/2,w*.75,h+40,w*.73,h-110).C(w*.71,h-200,w*.35,h-215,w*.44,h-300).C(w*.54,h-395,w-self.t/2,h-370,w-self.t/2,h*.28).C(w-self.t/2,self.t/2,w*.70,self.t/2,w*.38,self.t/2).stroke(self.t)
        self.add_char('ß',g,w,'s');self.add_char('ẞ',scale(g,1.12,self.cap/self.asc),w*1.12,'S')
        for c,base in [('ĸ','k'),('ſ','f')]:
            g,w=self.lower(base)
            if c=='ĸ':g=g.intersection(rect(-100,-230,1000,self.h))
            self.add_char(c,g,w,base)
        for c,seq in [('Ĳ','IJ'),('ĳ','ij'),('ŉ',"'n")]:
            pieces=[];x=0
            for ch in seq:
                n=self.cmap[ord(ch)];g,a,_,_=self.raw[n];pieces.append(move(g,x));x+=a-self.sb*.65
            self.add(gname(ord(c)),merge(*pieces),x+self.sb*.65,ord(c),seq[-1],(x/2,self.asc+55),(x/2,-44))
        for cp,c in [(0xAA,'a'),(0xBA,'o')]:
            g,w=self.lower(c);self.add_char(chr(cp),move(scale(g,.61),0,self.cap-self.h*.61),w*.61,c)

    def compose(self,cp):
        c=chr(cp);parts=ud.normalize('NFD',c)
        if len(parts)<2 or ord(parts[0]) not in self.cmap:return False
        marks=[ord(ch) for ch in parts[1:]]
        if not marks or any(m not in self.accents for m in marks):return False
        base=parts[0];n=self.cmap[ord(base)]
        if base in 'ij' and any(ud.combining(chr(m))==230 for m in marks):n=self.cmap[0x131 if base=='i' else 0x237]
        bg,a,top,bot=self.raw[n];gs=[bg];tx,ty=top;bx,by=bot
        for m in marks:
            mg=self.accent(m);cls=self.mark_info[gname(m)]['class']
            if cls=='bottom':x,y=bx,by;by+=mg.bounds[1]-40
            elif cls=='horn':x,y=bg.bounds[2]-self.t*.35,bg.bounds[3]-85
            elif cls=='overlay':x,y=a/2,self.h*.33
            else:x,y=tx,ty;ty+=mg.bounds[3]+45
            gs.append(move(mg,x,y))
        geom=merge(*gs)
        newtop=(a/2,max(ty,geom.bounds[3]+55));newbot=(a/2,min(by,geom.bounds[1]-44))
        self.add(gname(cp),geom,a,cp,base,newtop,newbot)
        return True
    def make_extended(self):
        # Every assigned Latin-1 / Extended-A character is explicitly covered.
        for cp in list(range(0xC0,0x250))+list(range(0x1E00,0x1F00)):
            if cp not in self.cmap:self.compose(cp)
        missing=[f'U+{cp:04X}' for cp in range(0xA0,0x180) if cp not in self.cmap and ud.category(chr(cp))!='Cn']
        if missing:raise RuntimeError('Required Latin coverage missing: '+', '.join(missing))
        # Accented alternates preserve consistency in words such as café / átomo.
        self.alt_maps={
            'ss01':{'a':'a.text'},'ss02':{'g':'g.double'},
            'ss03':{'y':'y.diagonal','i':'i.cut','j':'j.cut'},'ss04':{'R':'R.curved'}}
        for cp,n in list(self.cmap.items()):
            parts=ud.normalize('NFD',chr(cp))
            if len(parts)<2:continue
            for tag,bmap in [('ss01',{'a':'a.text'}),('ss02',{'g':'g.double'}),('ss03',{'y':'y.diagonal'}),('ss04',{'R':'R.curved'})]:
                if parts[0] not in bmap:continue
                bg,a,top,bot=self.raw[bmap[parts[0]]];gs=[bg];tx,ty=top;bx,by=bot
                for ch in parts[1:]:
                    m=ord(ch);mg=self.accent(m);cls=self.mark_info[gname(m)]['class']
                    if cls=='bottom':x,y=bx,by;by+=mg.bounds[1]-40
                    elif cls=='horn':x,y=bg.bounds[2]-self.t*.35,bg.bounds[3]-85
                    else:x,y=tx,ty;ty+=mg.bounds[3]+45
                    gs.append(move(mg,x,y))
                geom=merge(*gs);alt=n+'.'+tag
                self.add(alt,geom,a,base=parts[0],top=(a/2,geom.bounds[3]+55),bottom=(a/2,geom.bounds[1]-44))
                self.alt_maps[tag][n]=alt

    def make_alternates(self):
        t=self.t;w=490;h=self.h;sb=self.sb
        # ss01: conventional single-storey a with right stem, for restrained body use.
        aw=w-65
        ga=merge(self.bowl(aw),rect(aw-t,0,aw,h),rect(aw-t,0,w,t*.85))
        n=self.cmap[ord('a')];adv=self.glyphs[n].advance
        self.add('a.text',move(ga,sb),adv,base='a',top=(adv/2,h+55),bottom=(adv/2,-44))
        # ss02: two-storey g. The connector and ear are distinct from the default hook.
        upper=ring(22,h*.36,w-35,h,105,min(t*.82,112),self.k)
        lower=ring(0,self.desc,w,h*.20,112,min(t*.83,112),self.k)
        link=line([(w*.48,h*.40),(w*.33,h*.18),(w*.59,h*.10)],max(24,t*.75))
        gg=merge(upper,lower,link,rect(w*.68,h-t*.72,w+45,h))
        n=self.cmap[ord('g')];adv=self.glyphs[n].advance
        self.add('g.double',move(gg,sb),adv,base='g',top=(adv/2,h+55),bottom=(adv/2,self.desc-44))
        # ss03: diagonal y with the reference's forward-moving descender.
        gy=merge(line([(t*.45,h),(w*.47,h*.10)],t*.91),line([(w-t*.43,h),(w*.23,self.desc)],t*.98))
        n=self.cmap[ord('y')];adv=self.glyphs[n].advance
        self.add('y.diagonal',move(gy,sb),adv,base='y',top=(adv/2,h+55),bottom=(adv/2,self.desc-44))
        for c in 'ij':
            n=self.cmap[ord(c)];g,a,top,bot=self.raw[n];g=g.difference(rect(-500,h+1,2000,1400))
            center=(a/2 if c=='i' else self.sb+236-t/2)
            d=max(t,68);gd=poly([(center-d*.58,h+94),(center+d*.30,h+94),(center+d*.58,h+94+d),(center-d*.30,h+94+d)])
            self.add(c+'.cut',merge(g,gd),a,base=c,top=top,bottom=bot)
        # Curved-leg R alternate, usable independently of the diagonal y set.
        gr=merge(ring(0,self.cap*.42,547,self.cap,self.r+24,t,self.k),rect(0,0,t,self.cap),Curve(547*.44,self.cap*.45).C(547*.71,self.cap*.36,547*.64,self.cap*.10,565-t*.30,0).stroke(t*.94))
        self.add('R.curved',move(gr,sb),565+2*sb,base='R',top=((565+2*sb)/2,self.cap+55),bottom=((565+2*sb)/2,-44))
        z=self.cmap[ord('0')];g,a,top,bot=self.raw[z]
        slash=line([(self.sb+80,95),(self.sb+420,self.cap*.94-95)],max(24,t*.56))
        self.add('zero.slash',merge(g,slash),a,base='0',top=top,bottom=bot)
        # Numerical variants are genuinely distinct advance-width / scale records.
        for c in '0123456789':
            n=self.cmap[ord(c)];g,a,top,bot=self.raw[n]
            tab=640 if self.text else 620
            self.add(n+'.tnum',move(g,(tab-a)/2),tab,base=c,top=(tab/2,top[1]),bottom=(tab/2,bot[1]))
            for suffix,factor,y in [('numr',.54,350),('dnom',.54,0),('sups',.57,425),('subs',.57,-160)]:
                gg=move(scale(g,factor),18,y);aa=a*factor+36
                self.add(n+'.'+suffix,gg,aa,base=c,top=(aa/2,y+self.cap*factor+50),bottom=(aa/2,y-40))
        n='zero.slash';g,a,top,bot=self.raw[n];tab=640 if self.text else 620
        self.add('zero.slash.tnum',move(g,(tab-a)/2),tab,base='0',top=(tab/2,top[1]),bottom=(tab/2,bot[1]))
        for cp,c in [(0xB2,'2'),(0xB3,'3'),(0xB9,'1'),(0x2070,'0'),(0x2074,'4'),(0x2075,'5'),(0x2076,'6'),(0x2077,'7'),(0x2078,'8'),(0x2079,'9')]+[(0x2080+i,str(i)) for i in range(10)]:
            suffix='subs' if cp>=0x2080 else 'sups';g,a,top,bot=self.raw[self.cmap[ord(c)]+'.'+suffix]
            self.add(gname(cp),g,a,cp,c,top,bot)
        fg=line([(18,0),(330,self.cap*.94)],max(23,self.t*.58))
        self.add('fraction',move(fg,35),420,0x2044)
        for cp,pair in {0xBC:'14',0xBD:'12',0xBE:'34',0x2150:'17',0x2151:'19',0x2152:'1A',0x2153:'13',0x2154:'23',0x2155:'15',0x2156:'25',0x2157:'35',0x2158:'45',0x2159:'16',0x215A:'56',0x215B:'18',0x215C:'38',0x215D:'58',0x215E:'78'}.items():
            if pair=='1A':continue # 1/10 is not substituted with a fabricated denominator.
            g1,a1,_,_=self.raw[self.cmap[ord(pair[0])]+'.numr'];g2,a2,_,_=self.raw[self.cmap[ord(pair[1])]+'.dnom']
            x=a1-28;g=merge(g1,move(fg,x),move(g2,x+330));a=x+330+a2
            self.add(gname(cp),g,a,cp)
        ng,na,_,_=self.raw['one.numr'];dg,da,_,_=self.raw['one.dnom'];zg,za,_,_=self.raw['zero.dnom']
        xx=na-28;self.add(gname(0x2152),merge(ng,move(fg,xx),move(dg,xx+330),move(zg,xx+330+da)),xx+330+da+za,0x2152)
        # Ligatures preserve readable forms; tighter joins, not decorative code rewrites.
        for seq in ['ff','fi','fl','ffi','ffl','st','ct']:
            gs=[];x=0
            for i,c in enumerate(seq):
                n=self.cmap[ord(c)];g,a,_,_=self.raw[n]
                gs.append(move(g,x));x+=a-(36 if self.text else 44)
            adv=x+(36 if self.text else 44)
            self.add('_'.join(seq),merge(*gs),adv,base=seq[0],top=(adv/2,self.asc+55),bottom=(adv/2,-44))
        # Case-sensitive brackets/dashes are lifted for all-cap labels.
        for c in '()[]{}-–—«»‹›':
            n=self.cmap[ord(c)];g,a,top,bot=self.raw[n]
            self.add(n+'.case',move(g,0,78),a,base=c,top=top,bottom=bot)

    def build(self):
        self.make_basic();self.make_symbols();self.make_accents();self.make_special_latin()
        self.make_alternates();self.make_extended()
        return self

def gname(cp):
    if 65<=cp<=90 or 97<=cp<=122:return chr(cp)
    if 48<=cp<=57:return ['zero','one','two','three','four','five','six','seven','eight','nine'][cp-48]
    names={32:'space',160:'nbspace',46:'period',44:'comma',58:'colon',59:'semicolon',45:'hyphen',47:'slash',92:'backslash',39:'quotesingle',34:'quotedbl',40:'parenleft',41:'parenright',91:'bracketleft',93:'bracketright',123:'braceleft',125:'braceright',33:'exclam',63:'question',64:'at',38:'ampersand',42:'asterisk',43:'plus',61:'equal',60:'less',62:'greater',95:'underscore',124:'bar',35:'numbersign',36:'dollar',37:'percent'}
    return names.get(cp, f'uni{cp:04X}' if cp<=0xFFFF else f'u{cp:05X}')

def contours(g):
    """Yield clockwise exteriors and counter-clockwise counters for TrueType."""
    if g.is_empty:return
    polys=[g] if isinstance(g,Polygon) else [p for p in getattr(g,'geoms',[]) if isinstance(p,Polygon)]
    for p in sorted(polys,key=lambda p:(-p.area,p.bounds)):
        p=orient(p,sign=-1.0)
        for ring_ in [p.exterior,*p.interiors]:
            pts=list(ring_.coords)[:-1]
            if len(pts)>=3:yield pts

def draw_geometry(g,pen):
    for pts in contours(g):
        pp=[]
        for x,y in pts:
            point=(round(x),round(y))
            if not pp or point!=pp[-1]:pp.append(point)
        if len(pp)>1 and pp[0]==pp[-1]:pp.pop()
        if len(pp)<3:continue
        pen.moveTo(pp[0])
        for p in pp[1:]:pen.lineTo(p)
        pen.closePath()

def svg_path(g):
    lines=[]
    for pts in contours(g):
        lines.append('M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in pts)+' Z')
    return ' '.join(lines)
