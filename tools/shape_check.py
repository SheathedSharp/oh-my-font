#!/usr/bin/env python3
"""Optional HarfBuzz shaping checks using a locally available shared library.

No dependency is downloaded, no font is installed. If HarfBuzz is absent the
script explicitly reports 'not run', instead of treating the check as passed.
"""
from __future__ import annotations
import argparse,ctypes as C,ctypes.util,json,sys
from pathlib import Path
from fontTools.ttLib import TTFont

class Info(C.Structure):
    _fields_=[('codepoint',C.c_uint32),('mask',C.c_uint32),('cluster',C.c_uint32),('var1',C.c_uint32),('var2',C.c_uint32)]
class Pos(C.Structure):
    _fields_=[('x_advance',C.c_int32),('y_advance',C.c_int32),('x_offset',C.c_int32),('y_offset',C.c_int32),('var',C.c_uint32)]
class Feature(C.Structure):
    _fields_=[('tag',C.c_uint32),('value',C.c_uint32),('start',C.c_uint32),('end',C.c_uint32)]

class Shaper:
    def __init__(self):
        lib=ctypes.util.find_library('harfbuzz')
        if not lib:raise RuntimeError('HarfBuzz shared library not found; shaping checks were NOT run.')
        self.h=C.CDLL(lib)
        def sig(n,restype,argtypes):
            fn=getattr(self.h,n);fn.restype=restype;fn.argtypes=argtypes
        ptr=C.c_void_p
        sig('hb_blob_create',ptr,[ptr,C.c_uint,C.c_int,ptr,ptr]);sig('hb_blob_destroy',None,[ptr])
        sig('hb_face_create',ptr,[ptr,C.c_uint]);sig('hb_face_destroy',None,[ptr])
        sig('hb_font_create',ptr,[ptr]);sig('hb_font_destroy',None,[ptr])
        sig('hb_ot_font_set_funcs',None,[ptr]);sig('hb_font_set_scale',None,[ptr,C.c_int,C.c_int])
        sig('hb_buffer_create',ptr,[]);sig('hb_buffer_destroy',None,[ptr])
        sig('hb_buffer_add_utf8',None,[ptr,C.c_char_p,C.c_int,C.c_uint,C.c_int])
        sig('hb_buffer_guess_segment_properties',None,[ptr])
        sig('hb_feature_from_string',C.c_int,[C.c_char_p,C.c_int,C.POINTER(Feature)])
        sig('hb_shape',None,[ptr,ptr,C.POINTER(Feature),C.c_uint])
        sig('hb_buffer_get_glyph_infos',C.POINTER(Info),[ptr,C.POINTER(C.c_uint)])
        sig('hb_buffer_get_glyph_positions',C.POINTER(Pos),[ptr,C.POINTER(C.c_uint)])
    def shape(self,path:Path,text:str,features:list[str]|None=None):
        with TTFont(path) as f:names=f.getGlyphOrder();upm=f['head'].unitsPerEm
        data=path.read_bytes();bufdata=C.create_string_buffer(data)
        h=self.h;blob=h.hb_blob_create(bufdata,len(data),0,None,None)
        face=h.hb_face_create(blob,0);font=h.hb_font_create(face);buf=h.hb_buffer_create()
        try:
            h.hb_ot_font_set_funcs(font);h.hb_font_set_scale(font,upm,upm)
            utf=text.encode('utf8');h.hb_buffer_add_utf8(buf,utf,len(utf),0,len(utf));h.hb_buffer_guess_segment_properties(buf)
            fs=features or [];arr=(Feature*len(fs))()
            for i,item in enumerate(fs):
                if not h.hb_feature_from_string(item.encode('ascii'),-1,C.byref(arr[i])):raise ValueError('Bad feature '+item)
            h.hb_shape(font,buf,arr,len(fs));n=C.c_uint()
            ins=h.hb_buffer_get_glyph_infos(buf,C.byref(n));poss=h.hb_buffer_get_glyph_positions(buf,C.byref(n))
            return [{'glyph':names[ins[i].codepoint],'gid':ins[i].codepoint,'cluster':ins[i].cluster,
                     'advance':poss[i].x_advance,'x_offset':poss[i].x_offset,'y_offset':poss[i].y_offset} for i in range(n.value)]
        finally:
            h.hb_buffer_destroy(buf);h.hb_font_destroy(font);h.hb_face_destroy(face);h.hb_blob_destroy(blob)

def check(path:Path,s:Shaper):
    tests=[]
    def expect(text,features,expected):
        r=s.shape(path,text,features);actual=[x['glyph'] for x in r]
        if actual!=expected:raise AssertionError(f'{path.name}: {text!r} {features} -> {actual}, expected {expected}')
        tests.append({'text':text,'features':features,'glyphs':actual,'result':'passed'})
    expect('office',['liga=1'],['o','f_f_i','c','e'])
    expect('fi',['liga=0'],['f','i'])
    expect('á',['ss01=1'],['uni00E1.ss01'])
    expect('g',['ss02=1'],['g.double'])
    expect('yij',['ss03=1'],['y.diagonal','i.cut','j.cut'])
    expect('R',['ss04=1'],['R.curved'])
    expect('Il',['ss05=1'],['I.clarity','l.clarity'])
    expect('0',['zero=1','tnum=1'],['zero.slash.tnum'])
    expect('12/34',['frac=1'],['one.numr','two.numr','fraction','three.dnom','four.dnom'])
    expect('123',['sups=1'],['one.sups','two.sups','three.sups'])
    expect('123',['subs=1'],['one.subs','two.subs','three.subs'])
    expect('st',['dlig=1'],['s_t'])
    r=s.shape(path,'0123456789',['tnum=1'])
    if len({x['advance'] for x in r})!=1:raise AssertionError('Tabular widths differ after shaping')
    tests.append({'text':'0123456789','features':['tnum=1'],'advance':r[0]['advance'],'result':'passed'})
    rk=s.shape(path,'AV',['kern=1']);rn=s.shape(path,'AV',['kern=0'])
    if sum(x['advance'] for x in rk)>=sum(x['advance'] for x in rn):raise AssertionError('AV kerning not active')
    tests.append({'text':'AV','features':['kern=1'],'adjustment':sum(x['advance'] for x in rk)-sum(x['advance'] for x in rn),'result':'passed'})
    r=s.shape(path,'x\u0301\u0301',['mark=1','mkmk=1'])
    if not (len(r)==3 and r[1]['advance']==0 and r[2]['advance']==0 and r[2]['y_offset']>r[1]['y_offset']):raise AssertionError('Stacked mark placement failed: '+repr(r))
    tests.append({'text':'x\u0301\u0301','features':['mark=1','mkmk=1'],'positions':r,'result':'passed'})
    return {'file':path.name,'tests':tests,'passed':len(tests)}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('font_directory',type=Path);p.add_argument('--report',type=Path,default=Path('shaping-report.json'));a=p.parse_args()
    try:s=Shaper()
    except RuntimeError as e:print(e,file=sys.stderr);return 2
    paths=sorted(a.font_directory.rglob('*.ttf'))
    if not paths:raise SystemExit('No TTF files found in the specified directory.')
    report={'engine':'system HarfBuzz','records':[check(path,s) for path in paths], 'device_installation_tested':False}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'Passed shaping checks for {len(paths)} TTF faces; report: {a.report}')
    return 0
if __name__=='__main__':sys.exit(main())
