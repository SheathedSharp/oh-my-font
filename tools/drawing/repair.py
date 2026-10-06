"""Weight-specific optical repairs for the initial independent-master migration.

This module is NOT imported by production builds. Once migrated, edit a master's
stored paths: never regenerate an edited master from this historical scaffold.
"""
from outlines import Designer as LegacyDesigner
from outline_engine import Curve, rect, rr, merge, line, clean, move

# Explicit optical decisions for each cut, not values interpolated from one weight.
# (arch outer radius, counter roof thickness, e crossbar thickness, R leg attachment)
OPTICS = {
    'LihuiT': {
        100: (145, 19, 19, 7), 300: (153, 37, 35, 14),
        400: (167, 57, 53, 23), 500: (173, 73, 69, 29),
        600: (180, 88, 84, 35), 700: (187, 104, 100, 42),
        800: (196, 118, 113, 48), 900: (205, 134, 129, 55),
    },
    'zayJu': {
        100: (141, 20, 19, 7), 300: (151, 39, 37, 15),
        400: (163, 62, 58, 25), 500: (174, 80, 76, 32),
        600: (185, 98, 94, 40), 700: (196, 118, 113, 48),
        800: (207, 134, 128, 55), 900: (217, 150, 144, 62),
    },
}


def rounded_box(x0,y0,x1,y1,bl,br,tr,tl):
    """Independent corner radii; counter joins need not mirror outer shoulders."""
    cap=min((x1-x0)/2,(y1-y0)/2)
    bl,br,tr,tl=(max(0,min(v,cap)) for v in (bl,br,tr,tl));k=.5522847498307936
    p=Curve(x0+bl,y0).L(x1-br,y0)
    p.C(x1-br+k*br,y0,x1,y0+br-k*br,x1,y0+br).L(x1,y1-tr)
    p.C(x1,y1-tr+k*tr,x1-tr+k*tr,y1,x1-tr,y1).L(x0+tl,y1)
    p.C(x0+tl-k*tl,y1,x0,y1-tl+k*tl,x0,y1-tl).L(x0,y0+bl)
    p.C(x0,y0+bl-k*bl,x0+bl-k*bl,y0,x0+bl,y0)
    return p.poly()

class Designer(LegacyDesigner):
    def __init__(self, family='zayJu', weight=400, oblique=False):
        super().__init__(family, weight, oblique)
        self.optics = OPTICS[family][weight]

    def arch(self, w, h=None, stem_left=True):
        h = self.h if h is None else h
        t = self.t; r, roof, _, _ = self.optics
        r = min(r, w * .46)
        out = merge(rr(0, 0, w, h, r, .5523), rect(0, 0, r, r), rect(w-r, 0, w, r))
        # Counter ends below the baseline with STRAIGHT sides. A bottom-rounded
        # rectangle caused the Thin/Light flared feet at y=0..radius in 0.301.
        ir = min(max(18, r-t*.77), (w-2*t)/2)
        iy = h-roof; k = .5522847498307936
        p = Curve(t, -40).L(t, iy-ir)
        p.C(t, iy-ir+k*ir, t+ir-k*ir, iy, t+ir, iy).L(w-t-ir, iy)
        p.C(w-t-ir+k*ir, iy, w-t, iy-ir+k*ir, w-t, iy-ir)
        p.L(w-t, -40).L(t, -40)
        g = out.difference(p.poly())
        return merge(g, rect(0, 0, t, h)) if stem_left else g

    def lower(self, c):
        # Preserve the already distinct reference-led display cuts above Regular.
        if not self.text and self.weight >= 500:
            return super().lower(c)
        if c == 'e':
            t=self.t; h=self.h; w=self.cw-15
            r, roof, bar, _=self.optics; r=min(r,h*.32)
            split=h*.37
            # One exterior, one upper counter, one right aperture. The former
            # separate upper-ring/lower-stroke construction disconnected at Thin.
            k=.5522847498307936;ir=max(17,r-t)
            p=Curve(w-10,0).L(r,0)
            p.C(r-k*r,0,0,r-k*r,0,r).L(0,h-r)
            p.C(0,h-r+k*r,r-k*r,h,r,h).L(w-r,h)
            p.C(w-r+k*r,h,w,h-r+k*r,w,h-r).L(w,split+r)
            p.C(w,split+r-k*r,w-r+k*r,split,w-r,split)
            p.L(t,split).L(t,r)
            p.C(t,r-k*ir,r-k*ir,t,r,t).L(w-10,t).L(w-10,0)
            # The lower-left counter meets a crossbar/stem, not an outer bowl.
            # A large mirrored radius here produces an optically dark junction.
            upper=rounded_box(t,split+bar,w-t,h-roof,max(1,t*.06),max(12,r-bar),max(12,r-t),max(12,r-t))
            return clean(p.poly().difference(upper)),w
        return super().lower(c)

    def upper(self, c):
        if not self.text and self.weight >= 500:
            return super().upper(c)
        if c in 'DPR':
            t=self.t; h=self.cap; s=self.width_scale
            w={'D':690,'P':665,'R':700}[c]*s
            bw=w-16 if c=='R' else w
            y=0 if c=='D' else h*.39
            r=(180+t*.27)*(1 if c=='D' else (.84 if c=='R' else .81))
            r=min(r,(h-y)/2,bw/2); k=.5522847498307936
            # A single outer contour: no rounded bowl union protruding into the
            # upright stem. The counter keeps the family's rounded-square form.
            p=Curve(0,0).L(0,h).L(bw-r,h)
            p.C(bw-r+k*r,h,bw,h-r+k*r,bw,h-r).L(bw,y+r)
            p.C(bw,y+r-k*r,bw-r+k*r,y,bw-r,y).L(t,y).L(t,0).L(0,0)
            counter=rounded_box(t,y+t*.82,bw-t,h-t*.82,max(1,t*.06),max(20,r-t*.77),max(20,r-t*.77),max(1,t*.06))
            g=p.poly().difference(counter)
            if c=='R':
                # Attach inside the lower bar, never up in the enclosed counter.
                g=merge(g,line([(w*.49,y+self.optics[3]),(w-t*.3,0)],t*.98))
            return clean(g),w
        return super().upper(c)
