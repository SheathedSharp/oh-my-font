#!/usr/bin/env python3
"""Check actual full-reference WOFF2 use and the separate source-vector review UI."""
import argparse,hashlib,json,threading
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
from build import ROOT,FULL,OUT,FAMILIES,sha

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    p=argparse.ArgumentParser();p.add_argument('--browser',choices=('chromium','chrome'),default='chromium');a=p.parse_args()
    build=json.loads((OUT/'build.json').read_text());coverage=json.loads((FULL/'repertoire.json').read_text())['cmap']
    rows=[r for r in build['records'] if r['format']=='woff2'];expected={r['file'].split('/')[-1]:r['sha256'] for r in rows}
    page_html='<!doctype html><meta charset="utf-8"><title>Full reference font verification</title><style>body{padding:24px;background:#faf9f5;color:#171b1a}h2{font:20px system-ui}.sample{font-synthesis:none;font-size:42px;line-height:1.8;white-space:pre-wrap;overflow-wrap:anywhere}#warning{font:16px system-ui;color:#99372c}</style><div id="warning"></div>'
    sample='Build a brighter tomorrow. Quality & Rhythm.\nCafé, déjà vu, naïve — Straße & Æther.\nĎábel Ľudovít Ťažký Őrült Łódź Œuvre\nTiếng Việt: Nguyễn, Trường, cộng hòa\nĄą Ęę Įį Ųų Ǫǫ Ǭǭ  ⌘ ⌥ ⎋ ✓  0123456789'
    for family in FAMILIES:page_html+=f'<h2>{family} / full reference</h2><div id="{family}" class="sample"></div>'
    page_html+='<script>const repertoire=new Set('+json.dumps(list(map(int,coverage)))+');const families='+json.dumps(FAMILIES)+';window.renderSample=function(text){const missing=[...text].filter(c=>c!=="\\n"&&!repertoire.has(c.codePointAt(0)));document.querySelector("#warning").textContent=missing.length?"Unsupported: "+[...new Set(missing)].join(" "):"";for(const f of families)document.getElementById(f).textContent=missing.length?"":text;return missing.length===0};window.ready=Promise.all(families.map(async f=>{const face=new FontFace("Draft"+f,"url(fonts/"+f+"FullDraft-Reference.woff2)");await face.load();document.fonts.add(face);document.getElementById(f).style.fontFamily="Draft"+f;return{family:f,status:face.status}})).then(r=>{window.renderSample('+json.dumps(sample)+');return r});</script>'
    (OUT/'font-check.html').write_text(page_html)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}';errors=[];failed=[];loaded_hashes={}
    try:
      with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,**({'channel':'chrome'} if a.browser=='chrome' else {}))
        context=browser.new_context(viewport={'width':1500,'height':1200});page=context.new_page()
        page.on('pageerror',lambda e:errors.append(str(e)));page.on('requestfailed',lambda r:failed.append(r.url.removeprefix(base)))
        def response(res):
            if res.url.endswith('.woff2'):
                assert res.ok;loaded_hashes[res.url.rsplit('/',1)[-1]]=hashlib.sha256(res.body()).hexdigest()
        page.on('response',response);page.goto(base+'/.release-work/full-01/font-check.html');faces=page.evaluate('window.ready')
        assert len(faces)==2 and all(r['status']=='loaded' for r in faces) and loaded_hashes==expected
        assert page.locator('#warning').inner_text()==''
        cdp=context.new_cdp_session(page);cdp.send('DOM.enable');cdp.send('CSS.enable');root=cdp.send('DOM.getDocument')['root']['nodeId'];platform=[]
        for family in FAMILIES:
            node=cdp.send('DOM.querySelector',{'nodeId':root,'selector':'#'+family})['nodeId']
            fonts=cdp.send('CSS.getPlatformFontsForNode',{'nodeId':node})['fonts']
            assert fonts and all(f['isCustomFont'] and family in f['familyName'] for f in fonts),(family,fonts)
            platform.append({'family':family,'used_fonts':fonts})
        page.screenshot(path=str(OUT/'browser-actual-fonts.png'),full_page=True)
        assert not page.evaluate('window.renderSample("中文")')
        assert page.locator('#LihuiT').inner_text()==page.locator('#zayJu').inner_text()==''
        assert page.evaluate('window.renderSample("Café ąęįų Őrült")')
        page.goto(base+'/design/full-01/proofs/review.html');assert page.locator('#grid .tile').count()==72
        assert '986' in page.locator('#count').inner_text()
        page.locator('#next').click();assert '2 /' in page.locator('#count').inner_text()
        page.locator('#kind').select_option('core');assert page.locator('#grid .tile').count()==11
        page.locator('[data-family="zayJu"]').click();assert page.locator('#grid .tile').count()==11
        page.locator('#kind').select_option('all');page.locator('#search').fill('U+0105')
        assert page.locator('#grid .tile').count()==1
        page.locator('#grid .tile').click();assert 'uni0105' in page.locator('#title').inner_text()
        page.locator('#outline').check();assert page.locator('body').evaluate('e=>e.classList.contains("outline")')
        page.locator('#search').fill('中文');assert page.locator('#grid .tile').count()==0 and page.locator('#large svg').count()==0
        page.locator('#search').fill('');dimensions=[]
        for width in (1440,900,390):
            page.set_viewport_size({'width':width,'height':900});dims=page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
            assert dims['document']<=dims['viewport']+1;dimensions.append(dims)
        assert not errors and not failed
        report={'scope':'actual WOFF2 font-use check plus separate source-vector review; no visual approval inferred','browser':browser.version,
                'font_sha256':loaded_hashes,'fonts':faces,'platform_fonts':platform,'viewports':dimensions,
                'checks':['two exact full reference webfonts','Chrome reports only expected custom fonts in multilingual samples','unsupported scripts block preview','986-source-glyph directory per family','pagination','approved-core filter: 11 per family','individual codepoint search','outline toggle','no document-wide mobile overflow'],
                'page_errors':errors,'failed_requests':failed,'passed':True}
        context.close();browser.close();(OUT/'browser.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS: two exact full-reference WOFF2s; custom-font-only multilingual text; glyph review and missing-character guard; three viewports.')
    finally:server.shutdown();server.server_close();thread.join(timeout=3)
if __name__=='__main__':main()
