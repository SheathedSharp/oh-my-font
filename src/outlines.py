"""Reference-led LihuiT/zayJu redraw, revision 0.300.

All base Latin letters and digits are redrawn here. `outline_engine.py` supplies
geometry, accents, non-Latin-base symbols, encoding and composition. It never
reads fonts installed on the machine. Dimensions are our reconstructed values,
not an assertion that a raster specimen supplies original design masters.
"""
from __future__ import annotations
from outline_engine import *
from outline_engine import Designer as Engine
from pathlib import Path
import json
from shapely.geometry import shape
from shapely.ops import transform

_REFERENCE = json.loads((Path(__file__).with_name("reference_masters.json")).read_text(encoding="utf8"))

@lru_cache(maxsize=None)
def reference_outline(c,weight):
    entry=_REFERENCE[c];g=shape(entry["geometry"])
    if c=="y":
        bottom=g.bounds[1]
        g=transform(lambda x,y,z=None:(x,y*(-184/bottom) if y<0 else y),g)
    original_bounds=g.bounds
    delta=(STROKES["zayJu"][weight]-entry["nominal_stroke"])/2
    if delta:
        g=g.buffer(delta,quad_segs=12,join_style=1).buffer(0)
        if g.is_empty:raise ValueError("Empty reference-derived glyph: "+c)
        # Preserve baseline/xheight instead of synthetic scaling in the browser.
        b0=original_bounds;b=g.bounds
        sy=(b0[3]-b0[1])/(b[3]-b[1])
        g=move(g,-b[0],-b[1]);g=scale(g,1,sy);g=move(g,0,b0[1])
    return clean(g),g.bounds[2]


STROKES = {
    'zayJu': {100:24,300:48,400:76,500:98,600:121,700:145,800:165,900:185},
    'LihuiT':  {100:23,300:45,400:70,500:89,600:108,700:128,800:146,900:166},
}

class Designer(Engine):
    def __init__(self,family='zayJu',weight=400,oblique=False):
        super().__init__(family,weight,oblique)
        self.t=STROKES[family][weight]
        self.h=552 if self.text else 540
        self.cap=730; self.asc=738; self.desc=-184 if self.text else -184
        self.r=(141 if self.text else 133)+self.t*.36
        self.k=.565
        self.sb=57 if self.text else 32
        self.cw=530 if self.text else 610
        self.width_scale=.905 if self.text else 1

    def bowl(self,w=None,h=None,t=None,y=0,r=None):
        w=self.cw if w is None else w
        h=self.h if h is None else h;t=self.t if t is None else t
        rr_=self.r if r is None else r
        # Inner radii retain appreciable curvature in Bold/Black. Not square holes.
        outer=rr(0,y,w,h+y,rr_,.5523)
        inner=rr(t,y+t*.82,w-t,h+y-t*.82,max(18,rr_-t*.77),.5523)
        return outer.difference(inner)

    def curve_ring(self,w,h,r=None,t=None):
        t=self.t if t is None else t;r=self.r if r is None else r
        return rr(0,0,w,h,r,.5523).difference(rr(t,t*.82,w-t,h-t*.82,max(20,r-t*.77),.5523))

    def arch(self,w,h=None,stem_left=True):
        h=self.h if h is None else h;t=self.t;r=self.r
        # Shoulder and left junction differ: lower n is not a upside-down U.
        out=rr(0,0,w,h,r,.5523)
        out=merge(out,rect(0,0,r,r),rect(w-r,0,w,r))
        inner=rr(t,-30,w-t,h-t*.83,max(22,r-t*.77),.5523)
        inner=merge(inner,rect(t,-30,w-t,0))
        g=out.difference(inner)
        if stem_left:g=merge(g,rect(0,0,t,h))
        return g

    def shoulder(self,w,h=None):
        h=self.h if h is None else h;t=self.t;r=self.r
        return Curve(t/2,0).L(t/2,h-r).C(t/2,h-t/2,r*.64,h-t/2,r,h-t/2).L(w,h-t/2).stroke(t)

    def c_shape(self,w=None,h=None):
        w=self.cw if w is None else w;h=self.h if h is None else h
        t=self.t;r=min(self.r,h*.42)
        return Curve(w,h-t/2).L(r,h-t/2).C(t/2,h-t/2,t/2,h-r,t/2,h-r).L(t/2,r).C(t/2,t/2,r,t/2,r,t/2).L(w,t/2).stroke(t)

    def u_shape(self,w=None,h=None):
        w=self.cw if w is None else w;h=self.h if h is None else h;t=self.t;r=self.r
        return Curve(t/2,h).L(t/2,r).C(t/2,t/2,r,t/2,r,t/2).L(w-r,t/2).C(w-t/2,t/2,w-t/2,r,w-t/2,r).L(w-t/2,h).stroke(t)

    def n_shape(self,w=None,h=None):
        return self.arch(self.cw if w is None else w,h)

    def spiral_a(self,w=None):
        """Open, low diagonal tongue; wider and softer than the rejected a."""
        w=self.cw+35 if w is None else w;h=self.h;t=self.t
        # Continuous contour. No closed counter and no circular 'o' substitution.
        topx=w*.24; right_slope=w*.085; q=h*.60
        p=Curve(topx,h).L(w*.66,h)
        p.C(w*.80,h,w*.84,h-t*.20,w*.90,h-t*.78)
        p.L(w*.945,h-t*1.15).C(w*.99,h-t*1.65,w,h*.52,w,h*.43)
        p.L(w,h*.29).C(w,h*.095,w*.90,0,w*.78,0).L(w*.24,0)
        p.C(w*.085,0,0,h*.10,0,h*.265)
        p.C(0,h*.43,w*.105,q,w*.265,q).L(w*.69,q)
        p.C(w*.717,q,w*.732,q-t*.10,w*.730,q-t*.29)
        p.L(w*.730,q-t*.43).L(w*.45,q-t*1.03)
        p.L(w*.32,q-t*1.03)
        p.C(w*.22,q-t*1.03,w*.23,t,w*.315,t)
        p.L(w*.735,t).C(w*.79,t,w*.795,t*1.20,w*.795,t*1.53)
        p.L(w*.795,h*.44).C(w*.795,h*.59,w*.769,h-t*.78,w*.70,h-t)
        p.L(w*.10,h-t).L(topx,h)
        # Thin cuts need the same open-spiral topology but an optically narrower tongue.
        if t<92:
            r=min(self.r,h*.31)
            endx=w*.68; mid=h*.52
            center=Curve(w*.14,h-t/2).L(w-r,h-t/2)
            center.C(w-t/2,h-t/2,w-t/2,h-r,w-t/2,h-r).L(w-t/2,r)
            center.C(w-t/2,t/2,w-r,t/2,w-r,t/2).L(r,t/2)
            center.C(t/2,t/2,t/2,r,t/2,r)
            center.C(t/2,mid,r,mid,r,mid).L(endx,mid)
            return center.stroke(t)
        return p.poly()

    def open_g(self,w=None):
        """The specimen g is open: lower bowl does not touch the right stem."""
        w=self.cw if w is None else w;t=self.t;h=self.h;d=self.desc;r=self.r
        endx=w-t-max(43,t*.48)
        p=Curve(endx,t/2).L(r,t/2)
        p.C(t/2,t/2,t/2,r,t/2,r).L(t/2,h-r)
        p.C(t/2,h-t/2,r,h-t/2,r,h-t/2).L(w-r,h-t/2)
        p.C(w-t/2,h-t/2,w-t/2,h-r,w-t/2,h-r)
        p.L(w-t/2,d+r*.75)
        p.C(w-t/2,d+t/2,w-r*.65,d+t/2,w-r,d+t/2).L(t*.54,d+t/2)
        g=p.stroke(t)
        g=g.difference(poly([(endx-t*.37,0),(endx+8,0),(endx+8,t),(endx,t)]))
        g=g.difference(poly([(-60,d-20),(t*.52,d-20),(t*1.18,d+t+1),(-60,d+t+1)]))
        return g

    def open_y(self,w=None):
        """Two distinct strokes with deliberate clearance, as in the core row."""
        w=self.cw if w is None else w;t=self.t;h=self.h;d=self.desc;r=self.r*.84
        endx=w-t-max(40,t*.37)
        left=Curve(t/2,h).L(t/2,r)
        left.C(t/2,t/2,r,t/2,r,t/2).L(endx,t/2)
        g1=left.stroke(t)
        g1=g1.difference(poly([(endx-t*.36,0),(endx+6,0),(endx+6,t+1),(endx,t)]))
        right=Curve(w-t/2,h).L(w-t/2,d+r*.82)
        right.C(w-t/2,d+t/2,w-r*.50,d+t/2,w-r,d+t/2).L(t*.52,d+t/2)
        g2=right.stroke(t)
        g2=g2.difference(poly([(-70,d-20),(t*.49,d-20),(t*1.16,d+t+1),(-70,d+t+1)]))
        return merge(g1,g2)

    def text_a(self,w=None):
        w=self.cw if w is None else w;t=self.t;h=self.h
        # Conventional single-storey a used in the alphabet panel.
        return merge(self.bowl(w),rect(w-t,0,w,h))

    def lower(self,c):
        t=self.t;h=self.h;w=self.cw;r=self.r
        if not self.text and self.weight>=500 and c in _REFERENCE:
            g,w=reference_outline(c,self.weight)
            if c=='t':g=move(g,-62);w-=62
            return g,w
        if c=='a':
            w+=20 if self.text else 35
            g=self.text_a(w) if self.text else self.spiral_a(w)
        elif c=='b':g=merge(self.bowl(w),rect(0,r,t,self.asc))
        elif c=='c':w-=30;g=self.c_shape(w)
        elif c=='d':g=merge(self.bowl(w),rect(w-t,r,w,self.asc))
        elif c=='e':
            w-=15;split=h*.37;rad=min(r,h*.32);upperh=h-split
            # Larger curved bowl, long horizontal terminal, open right-side aperture.
            outer=rr(0,split,w,h,rad,.5523)
            inner=rr(t,split+t*.73,w-t,h-t*.76,max(17,rad-t*.76),.5523)
            upper=outer.difference(inner)
            leftbottom=Curve(t/2,h*.46).L(t/2,r)
            leftbottom.C(t/2,t/2,r,t/2,r,t/2).L(w-10,t/2)
            g=merge(upper,leftbottom.stroke(t))
        elif c=='f':
            w=382 if self.text else 410
            g=merge(self.shoulder(w,self.asc),rect(-38,h-t*.84,w*.91,h+t*.16))
            g=move(g,38);w+=38
        elif c=='g':g=self.open_g(w)
        elif c=='h':g=merge(self.arch(w),rect(0,0,t,self.asc))
        elif c=='i':
            w=t;dot=max(46,t);gap=max(55,(self.asc-h-dot)*.88)
            g=merge(rect(0,0,t,h),rr((t-dot)/2,h+gap,(t+dot)/2,h+gap+dot,min(dot*.20,27)))
        elif c=='j':
            w=248 if self.text else 285;dot=max(46,t);gap=max(55,(self.asc-h-dot)*.88)
            p=Curve(w-t/2,h).L(w-t/2,self.desc+105)
            p.C(w-t/2,self.desc+t/2,w-110,self.desc+t/2,w-130,self.desc+t/2).L(0,self.desc+t/2)
            g=merge(p.stroke(t),rr(w-t/2-dot/2,h+gap,w-t/2+dot/2,h+gap+dot,min(dot*.2,27)))
        elif c=='k':
            w-=30;g=merge(rect(0,0,t,self.asc),line([(w-t*.22,h),(t*.64,h*.41)],t*.91),line([(w*.44,h*.47),(w-t*.25,0)],t*.93))
        elif c=='l':
            if self.text:
                w=t+86;g=Curve(t/2,self.asc).L(t/2,100).C(t/2,t/2,95,t/2,112,t/2).L(w,t/2).stroke(t)
            else:w=t;g=rect(0,0,t,self.asc)
        elif c=='m':
            w=770 if self.text else 855;half=(w+t)/2
            g=merge(self.arch(half),move(self.arch(half),half-t))
        elif c=='n':g=self.arch(w)
        elif c=='o':g=self.bowl(w)
        elif c=='p':g=merge(self.bowl(w),rect(0,self.desc,t,h-r*.35))
        elif c=='q':g=merge(self.bowl(w),rect(w-t,self.desc,w,h-r*.35))
        elif c=='r':w=365 if self.text else 390;g=self.shoulder(w)
        elif c=='s':
            w-=38;g=self.s_shape(w,h)
        elif c=='t':
            w=336 if self.text else 370
            p=Curve(t/2,h+max(96,165-t*.30)).L(t/2,r)
            p.C(t/2,t/2,r,t/2,r,t/2).L(w,t/2)
            # Engine's make_basic adds 62 units to accommodate this left overhang.
            g=merge(p.stroke(t),rect(-62,h-t,w,h))
        elif c=='u':
            g=self.u_shape(w)
            # Slight upright at the end, rather than the rejected perfectly symmetric U.
            if t>=95:g=merge(g,rr(w-t,0,w,h,min(32,t*.21)))
        elif c=='v':w+=15;g=line([(t*.45,h),(w/2,t*.47),(w-t*.45,h)],t*.93)
        elif c=='w':
            w=790 if self.text else 855
            g=line([(t*.43,h),(w*.245,t*.45),(w*.5,h*.80),(w*.755,t*.45),(w-t*.43,h)],t*.93)
            # Keep the three upper terminals and lower turns within the reference box.
            g=g.intersection(rect(-20,0,w+20,h))
        elif c=='x':g=merge(line([(t*.38,0),(w-t*.38,h)],t*.92),line([(t*.38,h),(w-t*.38,0)],t*.92))
        elif c=='y':g=self.open_y(w)
        elif c=='z':
            w-=20;g=self.z_shape(w,h)
            rad=min(21,t*.15);g=g.buffer(-rad,quad_segs=12).buffer(rad,quad_segs=12)
        else:raise KeyError(c)
        return clean(g),w

    def upper(self,c):
        if not self.text and self.weight>=500 and c in _REFERENCE:
            return reference_outline(c,self.weight)
        t=self.t;h=self.cap;s=self.width_scale;w=690*s;r=180+t*.27
        def ring_(wid,hei=h,rad=r):return self.curve_ring(wid,hei,rad)
        if c=='A':
            w=740*s;g=merge(line([(t*.46,0),(w/2,h-t*.36),(w-t*.46,0)],t*.92),rect(w*.21,h*.34,w*.79,h*.34+t*.88))
        elif c=='B':
            w=750*s;mid=h*.50
            # Two unequal lobes with a softened central return, as in 'Build'.
            top=move(self.curve_ring(w-35,h-mid+t*.46,r*.84),0,mid-t*.46)
            bottom=self.curve_ring(w,mid+t*.45,r*.87)
            g=merge(top,bottom,rect(0,0,t,h))
        elif c=='C':w=675*s;g=self.c_shape(w,h)
        elif c=='D':g=merge(ring_(w),rect(0,0,t,h))
        elif c=='E':
            w=605*s;g=merge(self.c_shape(w,h),rect(0,h*.47,w*.85,h*.47+t*.91))
        elif c=='F':
            w=600*s;g=merge(self.shoulder(w,h),rect(0,h*.49,w*.86,h*.49+t*.91))
        elif c=='G':
            w=705*s;g=merge(self.c_shape(w,h),rect(w-t,0,w,h*.47),rect(w*.55,h*.47-t,w,h*.47))
        elif c=='H':g=merge(rect(0,0,t,h),rect(w-t,0,w,h),rect(0,h*.47,w,h*.47+t*.94))
        elif c=='I':
            w=(280 if self.text else t)
            g=rect((w-t)/2,0,(w+t)/2,h)
            if self.text:g=merge(g,rect(0,0,w,t*.70),rect(0,h-t*.70,w,h))
        elif c=='J':
            w=535*s
            p=Curve(w-t/2,h).L(w-t/2,r*.80)
            p.C(w-t/2,t/2,w-r,t/2,w-r,t/2).L(0,t/2);g=p.stroke(t)
        elif c=='K':
            w=700*s;g=merge(rect(0,0,t,h),line([(w-t*.26,h),(t*.66,h*.41)],t*.94),line([(w*.43,h*.48),(w-t*.29,0)],t*.95))
        elif c=='L':
            w=580*s
            p=Curve(t/2,h).L(t/2,max(60,t*.70))
            p.C(t/2,t/2,t*.72,t/2,t,t/2).L(w,t/2);g=p.stroke(t)
        elif c=='M':
            w=880*s;g=merge(rect(0,0,t,h),rect(w-t,0,w,h),line([(t*.48,h-t*.39),(w/2,h*.29),(w-t*.48,h-t*.39)],t*.95))
        elif c=='N':g=merge(rect(0,0,t,h),rect(w-t,0,w,h),line([(t*.55,h-t*.42),(w-t*.55,t*.42)],t*.93))
        elif c=='O':w=725*s;g=ring_(w)
        elif c=='P':
            w=665*s;g=merge(move(self.curve_ring(w,h*.61,r*.81),0,h*.39),rect(0,0,t,h))
        elif c=='Q':
            w=725*s;g=merge(ring_(w),line([(w*.63,h*.20),(w+10,-57)],t*.79))
        elif c=='R':
            w=700*s;g=merge(move(self.curve_ring(w-16,h*.61,r*.84),0,h*.39),rect(0,0,t,h),line([(w*.46,h*.45),(w-t*.3,0)],t*.98))
        elif c=='S':w=650*s;g=self.s_shape(w,h)
        elif c=='T':w=690*s;g=merge(rect(0,h-t,w,h),rect((w-t)/2,0,(w+t)/2,h))
        elif c=='U':g=self.u_shape(w,h)
        elif c=='V':w=740*s;g=line([(t*.45,h),(w/2,t*.43),(w-t*.45,h)],t*.96)
        elif c=='W':
            w=1000*s;g=line([(t*.46,h),(w*.235,t*.44),(w*.5,h*.80),(w*.765,t*.44),(w-t*.46,h)],t*.93)
            g=g.intersection(rect(-20,0,w+20,h))
        elif c=='X':g=merge(line([(t*.36,0),(w-t*.36,h)],t*.94),line([(t*.36,h),(w-t*.36,0)],t*.94))
        elif c=='Y':w=730*s;g=merge(line([(t*.4,h),(w/2,h*.40),(w-t*.4,h)],t*.94),rect((w-t)/2,0,(w+t)/2,h*.43))
        elif c=='Z':w=680*s;g=self.z_shape(w,h)
        else:raise KeyError(c)
        return clean(g),w

    def digit(self,d):
        if not self.text and self.weight>=500 and d in _REFERENCE:
            return reference_outline(d,self.weight)
        t=self.t;h=self.cap*.96;w=615 if not self.text else 544;r=self.r*1.12
        if d=='0':g=self.curve_ring(w,h,r)
        elif d=='1':
            w=314 if not self.text else 304
            flag=max(125,t*.78)
            g=poly([(0,h-flag),(w-t,h),(w,h),(w,0),(w-t,0),(w-t,h-t*1.25),(0,h-flag-t*.75)])
        elif d=='2':
            p=Curve(0,h-t/2).L(w-r,h-t/2)
            p.C(w-t/2,h-t/2,w-t/2,h-r,w-t/2,h-r).L(w-t/2,h*.64)
            p.C(w-t/2,h*.50,w-r,h*.49,w-r,h*.49).L(r,h*.49)
            p.C(t/2,h*.49,t/2,h*.39,t/2,h*.32).L(t/2,t/2).L(w,t/2);g=p.stroke(t)
        elif d=='3':
            mid=h*.5
            p=Curve(0,h-t/2).L(w-r,h-t/2).C(w-t/2,h-t/2,w-t/2,h-r,w-t/2,h-r)
            p.C(w-t/2,mid+t*.42,w-r,mid,w-r,mid)
            q=Curve(w-r,mid).C(w-t/2,mid,w-t/2,mid-t*.65,w-t/2,mid-t)
            q.L(w-t/2,r).C(w-t/2,t/2,w-r,t/2,w-r,t/2).L(0,t/2)
            g=merge(p.stroke(t),q.stroke(t),rect(w*.28,mid-t*.47,w-r*.80,mid+t*.47))
        elif d=='4':g=merge(line([(t/2,h),(t/2,h*.38),(w,h*.38)],t),rect(w-t*1.31,0,w-t*.31,h))
        elif d=='5':
            mid=h*.55
            p=Curve(t/2,mid).L(w-r,mid).C(w-t/2,mid,w-t/2,mid-r*.66,w-t/2,mid-r*.66)
            p.L(w-t/2,r).C(w-t/2,t/2,w-r,t/2,w-r,t/2).L(0,t/2)
            g=merge(p.stroke(t),rect(0,mid,t,h),rect(0,h-t,w,h))
        elif d=='6':
            g=merge(self.curve_ring(w,h*.62,r),self.c_shape(w,h).intersection(rect(-10,h*.18,w+20,h+10)))
        elif d=='7':g=merge(rect(0,h-t,w,h),line([(w-t*.48,h-t*.45),(w*.30,0)],t*.97))
        elif d=='8':g=merge(move(self.curve_ring(w-16,h*.53,r*.73),8,h*.47),self.curve_ring(w,h*.53,r*.78))
        elif d=='9':
            ringg=move(self.curve_ring(w,h*.62,r),0,h*.38)
            p=Curve(w-t/2,h*.60).L(w-t/2,r).C(w-t/2,t/2,w-r,t/2,w-r,t/2).L(0,t/2)
            g=merge(ringg,p.stroke(t))
        else:raise KeyError(d)
        return clean(g),w

    def make_alternates(self):
        # Reuse the encoding/feature inventory, then repair alternate dimensions.
        super().make_alternates()
        t=self.t;h=self.h;w=self.cw;sb=self.sb
        a_adv=self.glyphs['a'].advance
        ga=self.spiral_a(w+20) if self.text else self.text_a(w+35)
        self.add('a.text',move(ga,sb),a_adv,base='a',top=(a_adv/2,h+55),bottom=(a_adv/2,-44))
        for c in 'ij':
            n=self.cmap[ord(c)];g,a,top,bot=self.raw[n]
            g=g.difference(rect(-500,h+1,2000,1500))
            cx=(a/2 if c=='i' else self.sb+12+(248 if self.text else 285)-t/2)
            d=max(t,46);yy=h+max(55,(self.asc-h-d)*.88)
            gd=poly([(cx-d*.58,yy),(cx+d*.30,yy),(cx+d*.58,yy+d),(cx-d*.30,yy+d)])
            self.add(c+'.cut',merge(g,gd),a,base=c,top=top,bottom=bot)
        gy=merge(line([(t*.44,h),(w*.47,h*.09)],t*.92),line([(w-t*.44,h),(w*.23,self.desc)],t*.98))
        ya=self.glyphs['y'].advance
        self.add('y.diagonal',move(gy,sb),ya,base='y',top=(ya/2,h+55),bottom=(ya/2,self.desc-44))
        # LihuiT carries conventional distinguishable I/l, display has the specimen's bars.
        # Offer clarity alternates in BOTH families, independently of the diagonal-y set.
        iw=280;gi=merge(rect((iw-t)/2,0,(iw+t)/2,self.cap),rect(0,0,iw,t*.72),rect(0,self.cap-t*.72,iw,self.cap))
        self.add('I.clarity',move(gi,sb),iw+2*sb,base='I',top=((iw+2*sb)/2,self.cap+55),bottom=((iw+2*sb)/2,-44))
        lw=t+95;gl=Curve(t/2,self.asc).L(t/2,105).C(t/2,t/2,92,t/2,110,t/2).L(lw,t/2).stroke(t)
        self.add('l.clarity',move(gl,sb),lw+2*sb,base='l',top=((lw+2*sb)/2,self.asc+55),bottom=((lw+2*sb)/2,-44))
        ga=self.glyphs['g'].advance
        upper=ring(22,h*.36,w-35,h,128,min(t*.82,116),.5523)
        lower=ring(0,self.desc,w,h*.20,136,min(t*.80,116),.5523)
        link=line([(w*.48,h*.40),(w*.33,h*.18),(w*.59,h*.10)],max(24,t*.75))
        gg=merge(upper,lower,link,rect(w*.70,h-t*.72,w+20,h))
        self.add('g.double',move(gg,sb),ga,base='g',top=(ga/2,h+55),bottom=(ga/2,self.desc-44))
        rw=700*self.width_scale;ra=round(rw+2*sb)
        gr=merge(move(self.curve_ring(rw-16,self.cap*.61,180+t*.22),0,self.cap*.39),rect(0,0,t,self.cap),Curve(rw*.44,self.cap*.45).C(rw*.67,self.cap*.37,rw*.66,self.cap*.11,rw-t*.3,0).stroke(t*.94))
        self.add('R.curved',move(gr,sb),ra,base='R',top=(ra/2,self.cap+55),bottom=(ra/2,-44))
        zg,za,zt,zb=self.raw['zero'];xmin,ymin,xmax,ymax=zg.bounds
        slash=line([(xmin+t*.8,ymin+t*.6),(xmax-t*.8,ymax-t*.6)],max(24,t*.56))
        self.add('zero.slash',merge(zg,slash),za,base='0',top=zt,bottom=zb)
        # Update inherited tabular advance now that digits are substantially wider.
        target=max(self.glyphs[n].advance for n in ('zero','one','two','three','four','five','six','seven','eight','nine'))
        for n in ('zero','one','two','three','four','five','six','seven','eight','nine','zero.slash'):
            g,a,top,bot=self.raw[n];dx=(target-a)/2
            self.add(n+'.tnum',move(g,dx),target,base=self.glyphs[n].base,top=(target/2,top[1] if top else self.cap+55),bottom=(target/2,-44))
        for cp in (0x2007,):
            n=gname(cp);self.add(n,EMPTY,target,cp)
