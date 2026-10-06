#!/usr/bin/env python3
"""Export synchronized Glyphs companions without mutating authoritative UFOs.

The Glyphs-to-UFO return trip is checked for every outline, component placement,
advance and Unicode mapping. One editor format remains authoritative: the UFO.
"""
import argparse,hashlib,json
from pathlib import Path
from datetime import datetime
import glyphsLib,ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument,SourceDescriptor
from build import FULL,FAMILIES,load,signature,OUT,sha

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--check-only",action="store_true")
    args=parser.parse_args();records=[]
    for family in FAMILIES:
        u=load(family);before={p:sha(p) for p in Path(u.path).rglob('*') if p.is_file()}
        path=FULL/'sources'/f'{family}-Reference.glyphs'
        if not args.check_only:
            ds=DesignSpaceDocument();source=SourceDescriptor();source.font=u;source.path=str(u.path)
            source.name=family+'Reference';source.familyName=u.info.familyName;source.styleName=u.info.styleName;source.location={};ds.addSource(source)
            companion=glyphsLib.to_glyphs(ds,ufo_module=ufoLib2);companion.date=datetime(2026,10,6)
            with path.open('w',encoding='utf-8') as file:glyphsLib.dump(companion,file)
        returned=glyphsLib.to_ufos(glyphsLib.GSFont(str(path)),ufo_module=ufoLib2,generate_GDEF=False,propagate_anchors=False)
        if len(returned)!=1 or set(returned[0].keys())!=set(u.keys()):raise ValueError('Companion glyph inventory drift')
        back=returned[0]
        max_delta=0.0
        for name in u.keys():
            aw,ar=signature(u,name);bw,br=signature(back,name)
            if aw!=bw or len(ar)!=len(br) or u[name].unicodes!=back[name].unicodes:
                raise ValueError(f'Glyphs roundtrip changes {family}/{name}')
            for (op,points),(other,returned_points) in zip(ar,br):
                if op!=other or len(points)!=len(returned_points):raise ValueError('Contour operation drift')
                for p,q in zip(points,returned_points):
                    delta=max(abs(p[0]-q[0]),abs(p[1]-q[1]));max_delta=max(max_delta,delta)
                    if delta>0.00002:raise ValueError(f'Companion coordinate precision loss {family}/{name}: {delta}')
            a=sorted((r.name,r.x,r.y) for r in u[name].anchors);b=sorted((r.name,r.x,r.y) for r in back[name].anchors)
            if a!=b:raise ValueError(f'Anchor drift {family}/{name}')
        if any(sha(p)!=value for p,value in before.items()):raise ValueError('UFO changed during companion export')
        if '/Users/' in path.read_text() or '/home/' in path.read_text():raise ValueError('Private path in companion')
        records.append({'family':family,'glyphs_checked':len(u),'outlines_advances_mapping_anchors':'passed','companion_sha256':sha(path),'authoritative_ufo_unchanged':True,'max_coordinate_delta_upm':max_delta,'coordinate_precision_gate_upm':0.00002})
        print(f'{family}: {len(u)} Glyphs/UFO glyph roundtrips passed',flush=True)
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'glyphs-roundtrip.json').write_text(json.dumps({'records':records,'passed':True},indent=2)+'\n')
if __name__=='__main__':main()
