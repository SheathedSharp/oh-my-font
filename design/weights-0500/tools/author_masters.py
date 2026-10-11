#!/usr/bin/env python3
"""Write per-weight UFO masters from the approved Regular drawings.

Regular 400 upright is not rewritten: production builds it from the approved
reference UFO. Every other upright weight is a stored master. Oblique masters
are the matching upright master with a 10° slant, less slant inside counters,
and a per-weight sidebearing/aperture correction. They are not Italics.
"""
from __future__ import annotations
import math, re, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'design/weights-0500'))
sys.path.insert(0, str(ROOT / 'design/weights-0500/tools'))
from ufoLib2 import Font
from spec import FAMILIES, OBLIQUE_REGULAR, REFERENCE_STEMS, WEIGHT_NAMES, RATIONALE
from redraw import redraw_glyph

SOURCE = ROOT / 'design/full-01/sources'
OUT = ROOT / 'design/weights-0500/sources'
SHEAR = math.tan(math.radians(10))
APERTURE_GLYPHS = {'a', 'c', 'e', 'g', 's', 'C', 'G', 'S', 'a.text', 'g.double', 'two', 'three', 'six', 'nine'}

def _copy_font(family):
    src = SOURCE / f'{family}-Reference.ufo'
    work = OUT / family / '_work.ufo'
    if work.exists():
        shutil.rmtree(work)
    work.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, work)
    return Font.open(work)

def _style_name(weight, oblique):
    name = WEIGHT_NAMES[weight]
    if not oblique:
        return name
    return 'Oblique' if weight == 400 else f'{name} Oblique'

def _ps_name(family, weight, oblique):
    return family + '-' + _style_name(weight, oblique).replace(' ', '')

def _space_widths(font, spec):
    space = font['space'].width or 260
    factor = (space + spec['space_delta']) / space
    figure = font['zero.tnum'].width
    for glyph in font:
        if glyph.contours or glyph.components or glyph.width <= 0:
            continue
        if glyph.name in ('uni2007',):
            glyph.width = figure
        else:
            glyph.width = max(1, int(round(glyph.width * factor)))

def _anchor(glyph, name):
    for anchor in glyph.anchors:
        if anchor.name == name:
            return anchor
    return None

def _set_offset(component, x, y):
    xx, yx, xy, yy, _, _ = component.transformation
    component.transformation = (xx, yx, xy, yy, x, y)

def _offset(component):
    return component.transformation[4], component.transformation[5]

def _update_composites(font, original):
    for glyph in font:
        if glyph.contours or not glyph.components:
            continue
        old = original[glyph.name]
        first = glyph.components[0]
        first_base = font[first.baseGlyph]
        marks = [font[c.baseGlyph].lib.get('de.zayju.markClass') for c in glyph.components[1:]]
        accented = all(marks)
        if accented:
            sx = first.transformation[0] or 1
            old_base_width = original[first.baseGlyph].width
            right = old.width - _offset(old.components[0])[0] - sx * old_base_width
            _set_offset(first, _offset(first)[0], _offset(first)[1])
            glyph.width = max(0, int(round(_offset(first)[0] + sx * first_base.width + right)))
            for component, old_component, mark in zip(glyph.components[1:], old.components[1:], marks):
                old_anchor = _anchor(original[component.baseGlyph and first.baseGlyph], mark)
                new_anchor = _anchor(first_base, mark)
                if old_anchor is None or new_anchor is None:
                    continue
                ox, oy = _offset(old_component)
                # Scaled figures have no mark-class offset; accented letters do.
                if abs(sx - 1) > 0.01 and not font[component.baseGlyph].lib.get('de.zayju.markClass'):
                    continue
                _set_offset(component, new_anchor.x + (ox - old_anchor.x), new_anchor.y + (oy - old_anchor.y))
            _remap_composite_anchors(font, glyph, old, original, first_base)
        else:
            cursor_shift = 0
            for index, component in enumerate(glyph.components):
                old_component = old.components[index]
                if index == 0:
                    cursor_shift = font[component.baseGlyph].width - original[component.baseGlyph].width
                    continue
                ox, oy = _offset(old_component)
                _set_offset(component, ox + cursor_shift, oy)
                if not font[component.baseGlyph].lib.get('de.zayju.markClass'):
                    cursor_shift += font[component.baseGlyph].width - original[component.baseGlyph].width
            last = glyph.components[-1]
            last_base = font[last.baseGlyph]
            old_last = old.components[-1]
            sx = last.transformation[0] or 1
            old_right = old.width - _offset(old_last)[0] - sx * original[last.baseGlyph].width
            glyph.width = max(0, int(round(_offset(last)[0] + sx * last_base.width + old_right)))
            _remap_ligature_carets(glyph, old)

def _remap_composite_anchors(font, glyph, old, original, base):
    for anchor, old_anchor in zip(glyph.anchors, old.anchors):
        source = _anchor(base, anchor.name)
        old_source = _anchor(original[base.name], anchor.name)
        if source is None or old_source is None:
            continue
        anchor.x = source.x + (old_anchor.x - old_source.x)
        anchor.y = source.y + (old_anchor.y - old_source.y)
    # A top mark lifts the composite top anchor by the mark's own stacking anchor.
    for component in glyph.components[1:]:
        mark = font[component.baseGlyph]
        if mark is None or mark.lib.get('de.zayju.markClass') != 'top':
            continue
        stack = _anchor(mark, 'top')
        top = _anchor(glyph, 'top')
        if stack is None or top is None:
            continue
        ox, oy = _offset(component)
        top.x = ox + stack.x
        top.y = oy + stack.y

def _remap_ligature_carets(glyph, old):
    carets = [a for a in glyph.anchors if (a.name or '').startswith('caret')]
    old_carets = [a for a in old.anchors if (a.name or '').startswith('caret')]
    for index, (anchor, old_anchor) in enumerate(zip(carets, old_carets)):
        if index + 1 >= len(glyph.components):
            continue
        new_off = _offset(glyph.components[index + 1])[0]
        old_off = _offset(old.components[index + 1])[0]
        anchor.x = old_anchor.x + (new_off - old_off)

def _update_caret_records(font):
    carets = font.lib.get('de.zayju.ligatureCarets')
    if not carets:
        return
    text = font.features.text
    for name, values in list(carets.items()):
        glyph = font[name]
        found = [int(round(a.x)) for a in glyph.anchors if (a.name or '').startswith('caret')]
        if not found:
            continue
        carets[name] = found
        text = re.sub(rf'LigatureCaretByPos {name} [^;]+;', f'LigatureCaretByPos {name} ' + ' '.join(map(str, found)) + ';', text)
    font.features.text = text

def _scale_kerning(font, factor):
    for pair, value in list(font.kerning.items()):
        font.kerning[pair] = int(round(value * factor))

def _set_info(font, family, weight, oblique):
    style = _style_name(weight, oblique)
    font.info.familyName = family
    font.info.styleName = style
    font.info.openTypeOS2WeightClass = weight
    font.info.openTypeOS2WidthClass = 5
    font.info.postscriptFontName = _ps_name(family, weight, oblique)
    font.info.postscriptFullName = f'{family} {style}'
    font.info.openTypeNamePreferredFamilyName = family
    font.info.openTypeNamePreferredSubfamilyName = style
    font.info.italicAngle = -10 if oblique else 0
    font.info.openTypeNameDescription = (
        f'{family} {style}. Master redrawn from the approved 0.400 Regular; '
        + ('10° Oblique, not a separately drawn Italic. ' if oblique else 'Upright. ')
        + RATIONALE[family].get(weight, 'Regular oblique uses the approved drawing with slant corrections only.')
    )

def _note(glyph, family, weight, oblique):
    extra = RATIONALE[family].get(weight, 'Approved Regular drawing, slanted as Oblique.')
    glyph.lib['de.zayju.weight'] = weight
    glyph.lib['de.zayju.oblique'] = bool(oblique)
    if glyph.note:
        glyph.note = glyph.note.split('\nWeight master:')[0] + f'\nWeight master: {extra}'
    else:
        glyph.note = extra

def author_upright(family, weight):
    spec = FAMILIES[family][weight]
    refs = REFERENCE_STEMS[family]
    original = Font.open(SOURCE / f'{family}-Reference.ufo')
    font = _copy_font(family)
    changed = 0
    fallback = 0
    for glyph in font:
        if not glyph.contours:
            continue
        report = redraw_glyph(glyph, spec, refs)
        if report.get('counters', {}).get('fallback'):
            fallback += 1
        if report.get('changed'):
            changed += 1
        _note(glyph, family, weight, False)
    _space_widths(font, spec)
    _update_composites(font, original)
    _update_caret_records(font)
    _scale_kerning(font, spec['kern_scale'])
    _set_info(font, family, weight, False)
    return font, {'changed': changed, 'fallback': fallback}

def _shear_point(x, y, factor):
    return x + y * SHEAR * factor, y

def _contour_area(contour):
    ons = [(p.x, p.y) for p in contour.points if p.type]
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ons, ons[1:] + ons[:1])) / 2

def apply_oblique(font, family, weight, optical):
    """10° slant of this weight's own master, with less slant in counters."""
    keep = optical['counter_shear_keep']
    pad = optical['pad']
    aperture = optical['aperture']
    for glyph in font:
        if not glyph.contours:
            for anchor in glyph.anchors:
                anchor.x += anchor.y * SHEAR
            continue
        pre = [(p.x, p.y) for contour in glyph.contours for p in contour.points]
        old_xmin = min(p[0] for p in pre)
        old_xmax = max(p[0] for p in pre)
        old_ymax = max(p[1] for p in pre)
        old_ymin = min(p[1] for p in pre)
        for contour in glyph.contours:
            factor = 1 - keep if _contour_area(contour) < 0 else 1
            head = glyph.name.split('.')[0]
            xs = [p.x for p in contour.points]
            xmin, xmax = min(xs), max(xs)
            for point in contour.points:
                if head in APERTURE_GLYPHS and xmax > xmin and point.x > xmin + (xmax - xmin) * 0.72 and not glyph.lib.get('de.zayju.markClass'):
                    point.x += aperture * ((point.x - xmin) / (xmax - xmin) - 0.72)
                point.x, point.y = _shear_point(point.x, point.y, factor)
        post = [(p.x, p.y) for contour in glyph.contours for p in contour.points]
        new_xmin = min(p[0] for p in post)
        new_xmax = max(p[0] for p in post)
        if glyph.lib.get('de.zayju.markClass'):
            for anchor in glyph.anchors:
                if not (anchor.name or '').startswith('_'):
                    anchor.x += anchor.y * SHEAR
            continue
        # Restore the previous left sidebearing, then add this weight's oblique pad.
        shift = (old_xmin + pad) - new_xmin
        for contour in glyph.contours:
            for point in contour.points:
                point.x += shift
        right = glyph.width - old_xmax
        glyph.width = max(1, int(round(new_xmax + shift + right + pad + max(0, old_ymax) * SHEAR * 0.08)))
        for anchor in glyph.anchors:
            anchor.x += anchor.y * SHEAR + shift
        _note(glyph, family, weight, True)
    for pair, value in list(font.kerning.items()):
        font.kerning[pair] = int(round(value * 0.94))
    _set_info(font, family, weight, True)

def save_master(font, family, weight, oblique):
    from sanitize import sanitize_font
    sanitize_font(font)
    path = OUT / family / (_ps_name(family, weight, oblique).split('-', 1)[1] + '.ufo')
    if path.exists():
        shutil.rmtree(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    font.save(path, overwrite=True)
    return path

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for family in FAMILIES:
        uprights = {}
        for weight in FAMILIES[family]:
            font, report = author_upright(family, weight)
            path = save_master(font, family, weight, False)
            uprights[weight] = path
            print(family, weight, 'upright', report, path.name, flush=True)
        # Regular oblique starts from the approved drawing, not a retarget.
        regular = _copy_font(family)
        for glyph in regular:
            _note(glyph, family, 400, True)
        apply_oblique(regular, family, 400, OBLIQUE_REGULAR[family])
        # Composites still point at unsheared component offsets. Shear them
        # by rebuilding offsets from the sheared anchors / widths below.
        original = Font.open(SOURCE / f'{family}-Reference.ufo')
        _update_composites(regular, original)
        _update_caret_records(regular)
        path = save_master(regular, family, 400, True)
        print(family, 400, 'oblique', path.name, flush=True)
        for weight, upright_path in uprights.items():
            font = Font.open(upright_path)
            original_upright = Font.open(upright_path)
            apply_oblique(font, family, weight, FAMILIES[family][weight]['oblique'])
            _update_composites(font, original_upright)
            _update_caret_records(font)
            path = save_master(font, family, weight, True)
            print(family, weight, 'oblique', path.name, flush=True)

if __name__ == '__main__':
    main()
