#!/usr/bin/env python3
"""Migrate corrected historical scaffolds to independent, editable cubic masters.

Deliberately requires --output and refuses existing files. It is never called by
build.py or CI. Do not replace edited masters with regenerated scaffolds.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'tools/drawing/legacy'),str(ROOT/'.release-work/drawing-deps')]
from drawing.repair import Designer, OPTICS
from drawing.fit import fit_contour, fit_normalized
from drawing.finish import finish_svg
from outline_engine import contours
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.recordingPen import replayRecording
from outlines import WEIGHTS

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--families',nargs='+',default=['LihuiT','zayJu'])
    p.add_argument('--weights',nargs='+',type=int,default=list(WEIGHTS))
    a=p.parse_args();summaries=[];start=time.monotonic()
    targets=[a.output/family/f'{weight}.json' for family in a.families for weight in a.weights]
    if any(path.exists() for path in targets):raise SystemExit('Refusing to overwrite existing master(s). Use a new draft directory.')
    for family in a.families:
      for weight in a.weights:
        d=Designer(family,weight).build();glyphs=[];fallbacks=[];max_error=0;curves=0;fully_linear=0;contour_total=0
        for name,g in d.glyphs.items():
            pen=SVGPathPen(None);fcount=0
            for pts in contours(g.geometry):
                commands,error,fallback=fit_contour(pts)
                replayRecording(commands,pen);fcount+=fallback;contour_total+=1
                fully_linear+=not any(op=="curveTo" for op,args in commands)
                curves+=sum(op=='curveTo' for op,args in commands);max_error=max(max_error,error)
            if fcount:fallbacks.append({'glyph':name,'contours':fcount})
            glyphs.append({'name':name,'advance':g.advance,'unicodes':g.unicodes,'base':g.base,
                           'anchor_top':g.anchor_top,'anchor_bottom':g.anchor_bottom,'mark_class':g.mark_class,'path':finish_svg(pen.getCommands())[0]})
        # Some cmap aliases (e.g. nonbreaking space) are not repeated in the old
        # glyph.unicodes lists. Capture the exact authoritative mapping instead.
        for entry in glyphs:entry['unicodes']=[cp for cp,n in d.cmap.items() if n==entry['name']]
        data={'schema':1,'family':family,'weight':weight,'upm':1000,
              'metrics':{k:getattr(d,k) for k in ('t','h','cap','asc','desc','sb')},
              'glyph_count':len(glyphs),'codepoint_count':len(d.cmap),
              'origin':'0.301 original source, independent weight migration and junction repair; not a hand-drawn-from-scratch claim',
              'optical_profile':OPTICS[family][weight], 'alt_maps':d.alt_maps,'mark_info':d.mark_info}
        # One editable glyph per line keeps source diffs focused and reviewable.
        head=json.dumps(data,ensure_ascii=False,indent=2)
        text=head[:-2]+',\n  "glyphs": [\n'+',\n'.join('    '+json.dumps(g,ensure_ascii=False,separators=(',',':')) for g in glyphs)+'\n  ]\n}\n'
        target=a.output/family/f'{weight}.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8')
        summary={'family':family,'weight':weight,'glyphs':len(glyphs),'cubics':curves,'sampled_max_fit_error_upm':round(max_error,6),'preserved_line_contours':fallbacks,'contour_count':contour_total,'fully_linear_contours':fully_linear}
        summaries.append(summary)
        print(f'{family} {weight}: {len(glyphs)} glyphs, {curves} cubics, {len(fallbacks)} glyphs with preserved line contours, {time.monotonic()-start:.1f}s',flush=True)
    (a.output/'migration-report.json').write_text(json.dumps({'masters':summaries,'cache':str(fit_normalized.cache_info())},indent=2)+'\n')
if __name__=='__main__':main()
