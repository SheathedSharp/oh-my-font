#!/usr/bin/env python3
"""Verify real webfonts and interactive specimen in a fresh Chrome session.
Start a local server for site/ first. Never uses the user's browser profile.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8136/')
    parser.add_argument('--browser', choices=['chrome','chromium'], default='chrome')
    args = parser.parse_args()
    out = ROOT / '.release-work'
    out.mkdir(exist_ok=True)
    errors, responses, failed = [], {}, []
    report = {'url_scope': ('local HTTP' if args.url.startswith('http://127.0.0.1:') else 'published HTTP(S)') + ', fresh profile', 'viewports': [], 'checks': []}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome' if args.browser=='chrome' else None, headless=True)
        report['browser'] = browser.version
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: responses.update({response.url.split('/')[-1]: response.status}) if '.woff2' in response.url else None)
        page.on('requestfailed', lambda request: failed.append(request.url.split('/')[-1]))
        page.goto(args.url, wait_until='networkidle')
        page.wait_for_function("document.getElementById('font-status').textContent.startsWith('已加载真实')")
        loaded = page.evaluate('''async () => {
          const manifest = await (await fetch('font-manifest.json')).json();
          const rows = [];
          for (const face of manifest.fonts) {
            const found = await loadFace(face.family, face.weight, face.style);
            rows.push({file:face.file, family:face.family, weight:face.weight, style:face.style,
                       loaded:found.length > 0 && found.every(f => f.status === 'loaded')});
          }
          return rows;
        }''')
        assert len(loaded) == 32 and all(row['loaded'] for row in loaded)
        report['faces'] = loaded
        assert len(responses) == 32 and set(responses.values()) == {200}, responses
        report['checks'].append('32 exact webfont faces loaded; 32 successful WOFF2 responses')
        for width, height in [(1440, 1000), (900, 1000), (390, 844)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.reload(wait_until='networkidle')
            page.wait_for_function("document.getElementById('font-status').textContent.startsWith('已加载真实')")
            metrics = page.evaluate('({viewport:innerWidth, scroll:document.documentElement.scrollWidth})')
            assert metrics['scroll'] <= width, metrics
            assert page.locator('.specimen:not(.font-loaded)').count() == 0
            report['viewports'].append(metrics)
            page.screenshot(path=str(out / f'site-{width}.png'), full_page=True)
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.select_option('#family', 'LihuiT')
        page.select_option('#weight', '100')
        page.select_option('#style', 'oblique 10deg')
        page.wait_for_function("document.getElementById('font-status').textContent.includes('LihuiT / 100 / Oblique')")
        page.locator('[data-feature="ss05"]').check()
        setting = page.locator('#sample').evaluate('(e) => getComputedStyle(e).fontFeatureSettings')
        assert '"ss05"' in setting and '"ss05" 0' not in setting, setting
        page.locator('#sample').fill('字体测试 a g 0')
        assert page.locator('#coverage-warning').is_visible()
        report['checks'].append('Family/weight/Oblique/ss05 controls and missing-character warning')
        page.locator('#reset').click()
        page.wait_for_function("document.getElementById('font-status').textContent.includes('zayJu / 700 / Upright')")
        assert page.locator('#coverage-warning').is_hidden()
        page.locator('#theme').click()
        assert page.locator('html').get_attribute('data-theme') == 'dark'
        page.screenshot(path=str(out / 'site-dark.png'), full_page=True)
        page.locator('#all-glyphs').click()
        assert page.locator('#all-glyphs').get_attribute('aria-expanded') == 'true'
        assert page.locator('.glyph').count() > 700
        report['checks'].append('Reset, dark mode, complete glyph grid')
        broken = browser.new_page(viewport={'width': 390, 'height': 844})
        broken.route('**/*.woff2', lambda route: route.abort())
        broken.goto(args.url, wait_until='networkidle')
        broken.wait_for_function("document.getElementById('font-status').textContent.includes('字体加载失败')")
        assert broken.locator('#sample').get_attribute('data-loading') == 'true'
        report['checks'].append('Missing-font network failure is explicitly reported; no fallback specimen')
        broken.close()
        reduced = browser.new_page(reduced_motion='reduce')
        reduced.goto(args.url, wait_until='networkidle')
        assert reduced.locator('html').evaluate('(e) => getComputedStyle(e).scrollBehavior') == 'auto'
        reduced.close()
        report['checks'].append('Reduced-motion preference respected')
        browser.close()
    assert not errors, errors
    assert not failed, failed
    report['page_errors'] = errors
    report['failed_requests'] = failed
    (out / 'site-checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'faces'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
