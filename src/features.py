"""OpenType layout source generated from the actual glyph inventory."""
from __future__ import annotations
from outlines import Designer,gname

# Pair values are in 1000-UPM units; body spacing uses gentler corrections.
KERN_PAIRS={
 'AV':-68,'AW':-52,'AY':-70,'AT':-46,'AU':-14,'AO':-16,'AC':-16,'AG':-16,'AQ':-16,
 'VA':-68,'WA':-52,'YA':-70,'TA':-46,'To':-58,'Ta':-48,'Te':-56,'Tr':-28,'Tu':-25,
 'Ty':-30,'Tw':-25,'Ts':-38,'Tg':-45,'Tc':-54,'Tq':-50,'Td':-52,
 'Yo':-65,'Ya':-58,'Ye':-62,'Yr':-42,'Yu':-38,'Yg':-58,'Ys':-50,'Yc':-60,'Yq':-52,
 'Vo':-38,'Va':-38,'Ve':-38,'Vr':-20,'Vu':-20,'Vg':-32,'Vc':-38,
 'Wo':-28,'Wa':-26,'We':-28,'Wr':-14,'Wu':-14,'Wg':-24,'Wc':-28,
 'LT':-42,'LY':-66,'LV':-44,'LW':-35,'FA':-40,'Fo':-26,'Fa':-25,'Fe':-26,
 'PA':-36,'Po':-18,'Pa':-18,'Pe':-18,'OT':-14,'OY':-21,'OV':-18,'OW':-12,
 'DO':-6,'DY':-18,'DV':-12,'DT':-10,'RY':-16,'RV':-10,'RT':-6,
 'ro':-13,'ra':-8,'re':-12,'rc':-13,'rg':-8,'ry':-6,'rt':-5,
 'za':-5,'zy':-8,'yj':-7,'ju':-6,'ay':-8,'yo':-8,'va':-10,'vo':-12,'ve':-12,
 'wa':-8,'wo':-10,'we':-10,'ff':-12,'fo':-7,'fe':-7,
}

def build_features(d:Designer)->str:
    f=['languagesystem DFLT dflt;','languagesystem latn dflt;',
       'languagesystem latn TRK;','languagesystem latn AZE;',
       'languagesystem latn NLD;','languagesystem latn ROM;','']
    digits=[d.cmap[ord(c)] for c in '0123456789']
    for suffix in ['', '.tnum','.numr','.dnom','.sups','.subs']:
        tag='D'+suffix.replace('.','_')
        f.append(f'@{tag} = ['+' '.join(n+suffix for n in digits)+'];')
    marks=[n for n,g in d.glyphs.items() if g.mark_class]
    bases=[n for n,g in d.glyphs.items() if not g.mark_class and '_' not in n and n not in ['.notdef','.null','nonmarkingreturn']]
    ligs=['f_f','f_i','f_l','f_f_i','f_f_l','s_t','c_t']
    f += ['@BASE = ['+' '.join(bases)+'];','@MARK = ['+' '.join(marks)+'];',
          '@LIGATURE = ['+' '.join(ligs)+'];',
          'table GDEF { GlyphClassDef @BASE, @LIGATURE, @MARK, ; } GDEF;']
    # Turkish dotted-I localization is deliberately not faked by replacing I globally.
    # Canonical decompositions are handled in ccmp; precomposed outlines are also present.
    f.append('feature ccmp {')
    # Specific mark-context substitutions preserve the separate dot of i below-mark sequences.
    above=[n for n in marks if d.glyphs[n].mark_class=='top']
    f.append('  @AboveMarks = ['+' '.join(above)+'];')
    f.append("  sub i' @AboveMarks by uni0131;")
    f.append("  sub j' @AboveMarks by uni0237;")
    f.append('} ccmp;')
    for tag,description,mapping in [
      ('ss01','Open a' if d.text else 'Text a',[('a','a.text')]),
      ('ss02','Two-storey g',[('g','g.double')]),
      ('ss03','Diagonal y and cut dots',[('y','y.diagonal'),('i','i.cut'),('j','j.cut')]),
      ('ss04','Curved-leg R',[('R','R.curved')])]:
        f.append(f'feature {tag} {{')
        f.append(f'  featureNames {{ name "{description}"; }};')
        for x,y in d.alt_maps.get(tag,dict(mapping)).items():f.append(f'  sub {x} by {y};')
        f.append(f'}} {tag};')
    f += ['feature ss05 { featureNames { name "Clarity I and l"; }; sub I by I.clarity; sub l by l.clarity; } ss05;']
    f += ['feature zero { sub zero by zero.slash; sub zero.tnum by zero.slash.tnum; } zero;',
          'feature pnum { sub @D_tnum by @D; sub zero.slash.tnum by zero.slash; } pnum;',
          'feature tnum { sub @D by @D_tnum; sub zero.slash by zero.slash.tnum; } tnum;']
    for tag in ['numr','dnom','sups','subs']:
        f.append(f'feature {tag} {{ sub @D by @D_{tag}; }} {tag};')
    f += ['lookup Numerator { sub @D by @D_numr; } Numerator;',
          'lookup Denominator { sub @D by @D_dnom; } Denominator;',
          'feature frac {',
          "  sub @D slash' @D by fraction;",
          # Reverse scan consumes a whole numerator from right to left in one lookup.
          "  rsub @D' fraction by @D_numr;",
          "  rsub @D' @D_numr by @D_numr;",
          "  sub fraction @D' lookup Denominator;",
          "  sub @D_dnom @D' lookup Denominator;",
          '} frac;']
    f += ['feature ordn { sub a by uni00AA; sub o by uni00BA; } ordn;']
    f.append('feature liga {')
    for seq in ['ffi','ffl','ff','fi','fl']:
        f.append('  sub '+' '.join(seq)+' by '+'_'.join(seq)+';')
    f.append('} liga;')
    f.append('feature dlig { sub s t by s_t; sub c t by c_t; } dlig;')
    f.append('feature case {')
    for n in d.glyphs:
        if n.endswith('.case'):f.append(f'  sub {n[:-5]} by {n};')
    f.append('} case;')
    # Accent-aware class kerning: a precomposed letter inherits its Latin base class.
    groups={}
    for n,g in d.glyphs.items():
        if g.base and len(g.base)==1 and g.base in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' and not any(s in n for s in ['.numr','.dnom','.sups','.subs']) and '_' not in n:
            groups.setdefault(g.base,[]).append(n)
    for key,ns in sorted(groups.items()):f.append(f'@K_{key} = ['+' '.join(ns)+'];')
    f.append('feature kern { lookupflag IgnoreMarks;')
    factor=.77 if d.text else 1
    for pair,amount in sorted(KERN_PAIRS.items()):
        a,b=pair
        if a in groups and b in groups:f.append(f'  pos @K_{a} @K_{b} {round(amount*factor)};')
    f.append('} kern;')
    # Marks are drawn around (0,0), making their anchors exact, not guessed offsets.
    for n in marks:
        cl=d.glyphs[n].mark_class
        f.append(f'markClass {n} <anchor 0 0> @MC_{cl};')
    f.append('feature mark {')
    for n,g in d.glyphs.items():
        if n in ligs or g.mark_class or g.anchor_top is None:continue
        tx,ty=g.anchor_top; bx,by=g.anchor_bottom
        rawgeom,adv,_,_=d.raw[n]
        if rawgeom.is_empty:continue
        hx,hy=d.point((rawgeom.bounds[2]-d.t*.35,rawgeom.bounds[3]-85))
        ox,oy=d.point((adv/2,d.h*.33))
        f.append(f'  pos base {n} <anchor {round(tx)} {round(ty)}> mark @MC_top <anchor {round(bx)} {round(by)}> mark @MC_bottom <anchor {round(hx)} {round(hy)}> mark @MC_horn <anchor {round(ox)} {round(oy)}> mark @MC_overlay;')
    f.append('} mark;')
    f.append('feature mkmk {')
    for n in marks:
        cl=d.glyphs[n].mark_class
        if cl not in ['top','bottom']:continue
        yy=d.mark_info[n][cl];xx=d.shear*yy
        f.append(f'  pos mark {n} <anchor {round(xx)} {round(yy)}> mark @MC_{cl};')
    f.append('} mkmk;')
    return '\n'.join(f)+'\n'
