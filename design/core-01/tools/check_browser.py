#!/usr/bin/env python3
"""Exercise the limited-repertoire review UI and load both actual WOFF2 faces."""
from __future__ import annotations
import argparse,hashlib,json,threading
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright
from build import ROOT,STUDY,FAMILIES,CORE

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    p=argparse.ArgumentParser();p.add_argument('--browser',choices=['chrome','chromium'],default='chromium');a=p.parse_args()
    out=ROOT/'.release-work/core-01';build=json.loads((out/'build.json').read_text())
    expected={r['file'].split('/')[-1]:r['sha256'] for r in build['records'] if r['format']=='woff2'}
    html='<!doctype html><meta charset="utf-8"><title>Actual core webfonts</title><style>body{padding:24px;background:#faf9f5;color:#171b1a}section{font-synthesis:none;font-size:100px;margin:25px 0}h2{font:20px system-ui}</style>'
    for family in FAMILIES:
        html+=f'<h2>{family} Core Study 01</h2><section id="{family}">BMR age 23689<br>Rage Mega</section>'
    html+='<script>window.ready=Promise.all('+json.dumps(list(FAMILIES))+'.map(async(f)=>{const face=new FontFace("Study"+f,"url(fonts/"+f+"CoreStudy01-Reference.woff2)");await face.load();document.fonts.add(face);document.getElementById(f).style.fontFamily="Study"+f;return {family:f,status:face.status}}));</script>'
    (out/'font-check.html').write_text(html)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}';errors=[];failed=[];fonts={}
    try:
      with sync_playwright() as pw:
        kwargs={'headless':True}
        if a.browser=='chrome':kwargs['channel']='chrome'
        browser=pw.chromium.launch(**kwargs);context=browser.new_context(viewport={'width':1440,'height':1100})
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:failed.append(r.url.split(base)[-1]))
        def response(res):
            if res.url.endswith('.woff2'):
                name=res.url.rsplit('/',1)[-1];assert res.ok
                fonts[name]=hashlib.sha256(res.body()).hexdigest()
        page.on('response',response)
        page.goto(base+'/.release-work/core-01/font-check.html');loaded=page.evaluate('window.ready')
        assert len(loaded)==2 and all(r['status']=='loaded' for r in loaded)
        assert fonts==expected
        page.screenshot(path=str(out/'browser-actual-fonts.png'),full_page=True)
        page.goto(base+'/design/core-01/proofs/review.html')
        assert page.locator('#grid .tile').count()==11
        page.locator('[data-family="zayJu"]').click();assert page.locator('#detail-title').inner_text().startswith('zayJu')
        page.locator('#handles').check();page.locator('#outline').check()
        assert page.locator('body').evaluate('(e)=>e.classList.contains("nodes-on")&&e.classList.contains("outline-on")')
        page.locator('#sample').fill('Hello')
        assert page.locator('#warning').inner_text().startswith('未绘制字符') and page.locator('#stage svg').count()==0
        page.locator('#sample').fill('Rage  Mega');assert page.locator('#stage svg').count()==1
        page.locator('#grid .tile').nth(1).click();assert 'M' in page.locator('#detail-title').inner_text()
        dimensions=[]
        for width in (1440,900,390):
            page.set_viewport_size({'width':width,'height':900});page.evaluate('window.scrollTo(0,0)')
            dims=page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
            assert dims['document']<=dims['viewport']+1,dims;dimensions.append(dims)
        assert not errors and not failed
        report={'scope':'core-only browser/UI verification; not visual approval','browser':browser.version,'loaded_fonts':loaded,'font_sha256':fonts,
                'viewports':dimensions,'checks':['both exact WOFF2 faces loaded','11-glyph grid per family','family switch','curve outline and control-point toggles','unsupported text blocks rendering, no fallback','individual M enlargement','no document-wide mobile overflow'],
                'page_errors':errors,'failed_requests':failed,'passed':True}
        context.close();browser.close()
        (out/'browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('PASS: two exact webfonts; review controls and missing-character guard; 3 viewports.')
    finally:server.shutdown();server.server_close();thread.join(timeout=3)
if __name__=='__main__':main()
