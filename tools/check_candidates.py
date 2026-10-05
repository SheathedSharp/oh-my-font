#!/usr/bin/env python3
"""Check local candidates with OTS, exact identity/hash checks, and HarfBuzz.
No source font is overwritten or installed. Does not grant a distribution license.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import sys
import importlib.metadata
import ots
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from shape_check import check as shaping_check

ROOT = Path(__file__).resolve().parents[1]

class Shaper:
    def shape(self, path: Path, text: str, features: list[str] | None = None) -> list[dict]:
        with TTFont(path) as font:
            names = font.getGlyphOrder()
            upm = font['head'].unitsPerEm
            font.flavor = None
            data = io.BytesIO()
            font.save(data)
        face = hb.Face(data.getvalue())
        font = hb.Font(face)
        font.scale = (upm, upm)
        hb.ot_font_set_funcs(font)
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.guess_segment_properties()
        settings = {key: int(value) for key, value in (item.split('=') for item in (features or []))}
        hb.shape(font, buffer, settings)
        return [{'glyph': names[info.codepoint], 'gid': info.codepoint, 'cluster': info.cluster,
                 'advance': pos.x_advance, 'x_offset': pos.x_offset, 'y_offset': pos.y_offset}
                for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions)]

def main() -> int:
    paths = sorted(path for fmt in ('ttf', 'otf', 'woff2') for path in (ROOT / 'dist' / fmt).glob(f'*/*.{fmt}'))
    if len(paths) != 96:
        raise SystemExit('Expected exactly 96 font candidates.')
    binary = Path(ots.__file__).with_name('ots-sanitize')
    if not binary.is_file():
        raise SystemExit('OpenType Sanitizer executable missing.')
    output = ROOT / '.release-work'
    output.mkdir(exist_ok=True)
    report = {'versions': {name: importlib.metadata.version(name) for name in ('fonttools', 'uharfbuzz', 'opentype-sanitizer')}, 'records': [], 'scope': 'local candidate; no installation or license approval'}
    with tempfile.TemporaryDirectory(prefix='ots-', dir=output) as temp:
        for index, path in enumerate(paths):
            original = hashlib.sha256(path.read_bytes()).hexdigest()
            record = {'file': path.relative_to(ROOT / 'dist').as_posix(), 'sha256': original}
            result = subprocess.run([str(binary), str(path), str(Path(temp) / f'{index}.sfnt')], capture_output=True, text=True)
            record['ots_exit'] = result.returncode
            record['ots_messages'] = (result.stdout + result.stderr).replace(str(ROOT), '<project>')
            with TTFont(path) as font:
                record.update(family=font['name'].getDebugName(16), style=font['name'].getDebugName(17), codepoints=len(font.getBestCmap()))
                assert record['family'] in ('LihuiT', 'zayJu')
                assert font['name'].getDebugName(9) == 'zayju'
                assert all(not any(old in n.toUnicode() for old in ('Zixian', 'Lihui ')) for n in font['name'].names)
                assert font['head'].fontRevision > 0.300
                assert font['OS/2'].ulCodePageRange1 > 0
                assert font['post'].underlineThickness == 50
            try:
                shaped = shaping_check(path, Shaper())
                record['shaping_passed'] = shaped['passed']
                record['shaping_tests'] = shaped['tests']
            except (AssertionError, ValueError, RuntimeError) as error:
                record['shaping_error'] = str(error).replace(str(ROOT), '<project>')
            assert hashlib.sha256(path.read_bytes()).hexdigest() == original
            report['records'].append(record)
            print(f"{record['file']}: OTS={result.returncode}, shaping={record.get('shaping_passed', 'FAILED')}", flush=True)
    (output / 'candidate-checks.json').write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n')
    passed = all(r['ots_exit'] == 0 and r.get('shaping_passed') == 15 for r in report['records'])
    print('PASS' if passed else 'CHECKS FAILED', len(paths), 'candidates')
    return 0 if passed else 1

if __name__ == '__main__':
    sys.exit(main())
