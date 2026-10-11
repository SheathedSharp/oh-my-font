#!/usr/bin/env python3
"""Make stored 0.500 masters survive integer compilation.

The weight drawings stay the measured cubics. A join that doubles back into a
knot is still the same stroke until coordinates are rounded; rounding, and the
TrueType quadratic step after it, turns the knot into a self-intersection.
This tool cuts those revisits and resamples the contour onto the same curve.
It does not buffer Regular and it does not invent a new stem.

A scaled figure (superior, fraction, case punctuation) that still crosses after
its component transform is stored as its own repaired outline of that
transformed drawing. Stored masters must be compiled without overlap removal:
pathops puts the knots back. Regular 400 upright is not in this directory.
"""
from __future__ import annotations
import argparse, itertools, math, sys
from functools import lru_cache
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'design/core-01/tools'))
sys.path.insert(0, str(ROOT / 'design/weights-0500/tools'))
import geometry
import ufo2ft
from fontTools.pens.recordingPen import DecomposingRecordingPen
from ufo2ft.filters.decomposeTransformedComponents import DecomposeTransformedComponentsFilter
from fontTools.misc.roundTools import otRound
from ufoLib2 import Font
from ufoLib2.objects import Component, Glyph
from redraw import read_segments, _sample_segment, _area
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon
from shapely.validation import make_valid

REVIEW = ('A', 'B', 'M', 'R', 'a', 'g', 'e', 'two', 'three', 'six', 'eight', 'nine')
DIGITS = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine')
TABULAR = tuple(f'{name}.tnum' for name in DIGITS) + ('zero.slash.tnum',)


def _ink_span(glyph):
    xs = [point.x for contour in glyph.contours for point in contour.points]
    if not xs:
        return None
    return min(xs), max(xs)


def _shift_x(glyph, delta):
    if abs(delta) < 1e-9:
        return
    for contour in glyph.contours:
        for point in contour.points:
            point.x += delta
    for anchor in glyph.anchors:
        anchor.x += delta


def retabulate(font):
    """Give this master's tabular figures one advance.

    The shared width is the widest proportional digit (or slashed zero) of
    *this* master, raised if a decomposed tabular drawing is wider than that.
    Component figures keep their base and are recentered. Decomposed figures
    are translated so the ink is centered. Proportional digit drawings stay.
    """
    spans = []
    for name in DIGITS + ('zero.slash',):
        if name in font:
            spans.append(font[name].width or 0)
    for name in TABULAR:
        if name not in font:
            continue
        glyph = font[name]
        if glyph.contours:
            box = _ink_span(glyph)
            if box:
                spans.append(box[1] - box[0])
        elif len(glyph.components) == 1:
            xx = glyph.components[0].transformation[0]
            spans.append(abs(xx) * (font[glyph.components[0].baseGlyph].width or 0))
    if not spans:
        return 0
    target = int(math.ceil(max(spans) - 1e-9))
    for name in TABULAR:
        if name not in font:
            continue
        glyph = font[name]
        if glyph.contours and glyph.components:
            raise ValueError(f'{name}: tabular glyph mixes contours and components')
        if glyph.contours:
            box = _ink_span(glyph)
            ink = box[1] - box[0]
            shift = (target - ink) / 2 - box[0]
            if abs(shift) >= 0.5:
                _shift_x(glyph, float(round(shift)))
        elif len(glyph.components) == 1:
            component = glyph.components[0]
            xx, yx, xy, yy, x, y = component.transformation
            advance = abs(xx) * (font[component.baseGlyph].width or 0)
            new_x = float(round((target - advance) / 2))
            _shift_x(glyph, new_x - x)
            component.transformation = (xx, yx, xy, yy, new_x, y)
        elif glyph.components:
            raise ValueError(f'{name}: tabular glyph has {len(glyph.components)} components')
        glyph.width = target
    if 'uni2007' in font:
        font['uni2007'].width = target
    return target


def _named_anchor(glyph, name):
    for anchor in glyph.anchors:
        if anchor.name == name:
            return anchor
    return None


@lru_cache(maxsize=None)
def _reference_font(family):
    path = ROOT / 'design/full-01/sources' / f'{family}-Reference.ufo'
    if not path.is_dir():
        return None
    return Font.open(path)


def _reference_bases(font, name):
    """Approved component bases. The construction note can name i.cut while the
    glyph actually uses the dotless stem, so a baked accent must follow the
    reference components.
    """
    family = font.info.familyName
    if not family:
        return None
    source = _reference_font(family)
    if source is None or name not in source or len(source[name].components) < 2:
        return None
    bases = [component.baseGlyph for component in source[name].components]
    if any(base not in font for base in bases):
        return None
    if not all(font[base].lib.get('de.zayju.markClass') for base in bases[1:]):
        return None
    return bases


def _accent_construction(font, glyph):
    """Base plus marks, either still components or baked back to contours."""
    if len(glyph.components) >= 2:
        marks = [font[component.baseGlyph].lib.get('de.zayju.markClass') for component in glyph.components[1:]]
        if all(marks):
            return [(component.baseGlyph, component.transformation) for component in glyph.components]
    if glyph.contours:
        bases = _reference_bases(font, glyph.name)
        if bases is None:
            construction = glyph.lib.get('de.zayju.construction')
            if isinstance(construction, list) and len(construction) >= 2 and all(name in font for name in construction) and all(font[name].lib.get('de.zayju.markClass') for name in construction[1:]):
                bases = list(construction)
        if bases:
            return [(name, (1, 0, 0, 1, 0, 0)) for name in bases]
    return None


def _contour_area(contour):
    ons = [(point.x, point.y) for point in contour.points if point.type]
    if len(ons) < 3:
        return 0
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ons, ons[1:] + ons[:1])) / 2


def drop_horn_spurs(font):
    """Drop the reversed 4-point kink on the horn mark.

    It is not a counter. Kept in the same glyph as the base, it punches a hole
    through U; drawn as its own mark, the base fills that hole back. The two
    results then disagree by about 5 UPM.
    """
    glyph = font.get('uni031B')
    if glyph is None or len(glyph.contours) < 2:
        return 0
    kept = []
    dropped = 0
    for contour in glyph.contours:
        ons = [point for point in contour.points if point.type]
        if len(ons) <= 4 and abs(_contour_area(contour)) < 80:
            dropped += 1
            continue
        kept.append(contour)
    if dropped:
        glyph.contours = kept
    return dropped


def restack_marks(font):
    """Place accent components on this master's own anchors.

    A second mark stacks on the mark under it. The old Regular gap is not
    reused: the combining marks were redrawn, so their stacking anchors moved.
    Oblique anchors were sheared; the components follow those anchors.
    """
    moved = restored = 0
    for glyph in font:
        parts = _accent_construction(font, glyph)
        if parts is None:
            continue
        baked = bool(glyph.contours) or len(glyph.components) < 2
        if baked:
            glyph.clearContours()
            glyph.clearComponents()
            for name, _ in parts:
                glyph.components.append(Component(name, (1, 0, 0, 1, 0, 0)))
            glyph.lib['de.zayju.construction'] = [name for name, _ in parts]
            restored += 1
        base_component = glyph.components[0]
        base = font[base_component.baseGlyph]
        xx, yx, xy, yy, bx, by = base_component.transformation
        if abs(xx - 1) > 1e-6 or abs(yx) > 1e-6 or abs(xy) > 1e-6 or abs(yy - 1) > 1e-6:
            raise ValueError(f'{glyph.name}: accent base is scaled')
        bx, by = otRound(bx), otRound(by)
        placed = []
        for component in glyph.components[1:]:
            mark = font[component.baseGlyph]
            kind = mark.lib.get('de.zayju.markClass')
            attach = _named_anchor(mark, f'_{kind}')
            if attach is None:
                raise ValueError(f'{glyph.name}: {mark.name} has no _{kind} anchor')
            host = None
            for previous_kind, ox, oy, previous in reversed(placed):
                if previous_kind != kind:
                    continue
                stack = _named_anchor(previous, kind)
                if stack is None:
                    continue
                host = (ox + otRound(stack.x), oy + otRound(stack.y))
                break
            if host is None:
                base_anchor = _named_anchor(base, kind)
                if base_anchor is None:
                    raise ValueError(f'{glyph.name}: {base.name} has no {kind} anchor')
                host = (bx + otRound(base_anchor.x), by + otRound(base_anchor.y))
            mx, my = host[0] - otRound(attach.x), host[1] - otRound(attach.y)
            cxx, cyx, cxy, cyy, _, _ = component.transformation
            if abs(cxx - 1) > 1e-6 or abs(cyx) > 1e-6 or abs(cxy) > 1e-6 or abs(cyy - 1) > 1e-6:
                raise ValueError(f'{glyph.name}: accent {mark.name} is scaled')
            component.transformation = (1, 0, 0, 1, float(mx), float(my))
            placed.append((kind, mx, my, mark))
            moved += 1
        last = {}
        for kind, ox, oy, mark in placed:
            stack = _named_anchor(mark, kind)
            if stack is not None:
                last[kind] = (ox + otRound(stack.x), oy + otRound(stack.y))
        for anchor in glyph.anchors:
            if anchor.name in last:
                anchor.x, anchor.y = last[anchor.name]
            else:
                source = _named_anchor(base, anchor.name)
                if source is not None:
                    anchor.x = bx + otRound(source.x)
                    anchor.y = by + otRound(source.y)
    dropped = drop_horn_spurs(font)
    return {'mark_components': moved, 'restored_accents': restored, 'horn_spurs': dropped}


def _dedup(pts):
    out = []
    for point in pts:
        if not out or point != out[-1]:
            out.append(point)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def _shoelace(pts):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2)


def _polygons(geom):
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, (MultiPolygon, GeometryCollection)):
        found = []
        for item in geom.geoms:
            found.extend(_polygons(item))
        return found
    return []


def _cut_revisits(pts, max_area=500):
    """Drop a short out-and-back that returns to the same integer point."""
    pts = _dedup(pts)
    for _ in range(24):
        seen, best = {}, None
        for index, point in enumerate(pts):
            if point in seen and index - seen[point] >= 4:
                start = seen[point]
                area = _shoelace(pts[start:index + 1])
                if area <= max_area and (best is None or area < best[0]):
                    best = (area, start, index)
            seen[point] = index
        if best is None:
            break
        _, start, index = best
        pts = _dedup(pts[:start + 1] + pts[index + 1:])
    return pts


def _orient(pts, positive):
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2
    if abs(area) < 0.5:
        return []
    if (positive and area < 0) or ((not positive) and area > 0):
        return list(reversed(pts))
    return pts


def _integer_ring(poly):
    """Round onto the integer grid, resolving the tiny crossings that rounding adds."""
    current = poly
    for _ in range(4):
        ring = _dedup((int(round(x)), int(round(y))) for x, y in current.exterior.coords)
        if len(ring) < 3:
            return []
        integer = Polygon(ring)
        if integer.is_valid:
            return ring
        pieces = _polygons(make_valid(integer))
        if not pieces:
            return []
        current = max(pieces, key=lambda item: item.area)
    return []


def _trace(segs):
    """Curve samples stay dense. Straight segments stay at their corners."""
    raw = []
    for seg in segs:
        if seg['kind'] == 'line':
            raw.append(seg['p0'])
            raw.append(seg['p1'])
        else:
            raw.extend(_sample_segment(seg, 16))
    return _dedup([(float(x), float(y)) for x, y in raw])


def _nudge_junctions(raw, positive, reference_area):
    """Separate integer points that rounding piled on one junction.

    A real crossing of the measured curve is left alone. This only runs when
    the float contour was valid and rounding collapsed distinct visits onto
    one grid point.
    """
    if len(raw) > 48:
        return None
    reference = LineString(raw)
    pts = _dedup((int(round(x)), int(round(y))) for x, y in raw)
    offsets = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]

    def accept(candidate):
        candidate = _dedup(candidate)
        if len(candidate) < 3 or not Polygon(candidate).is_valid:
            return None
        if any(reference.distance(Point(point)) > 1.6 for point in candidate):
            return None
        area = Polygon(candidate).area
        if reference_area > 1 and not 0.90 <= area / reference_area <= 1.10:
            return None
        return candidate

    agreed = accept(pts)
    if agreed:
        return _orient(agreed, positive)
    groups = {}
    for index, point in enumerate(pts):
        groups.setdefault(point, []).append(index)
    extras = [(index, pts[index]) for indexes in groups.values() if len(indexes) > 1 for index in indexes[1:]]
    if not extras or len(extras) > 3:
        return None
    best = None
    for choice in itertools.product(offsets, repeat=len(extras)):
        trial = list(pts)
        for (index, base), (dx, dy) in zip(extras, choice):
            trial[index] = (base[0] + dx, base[1] + dy)
        agreed = accept(trial)
        if agreed is None:
            continue
        error = abs(Polygon(agreed).area - reference_area)
        if best is None or error < best[0]:
            best = (error, agreed)
    return _orient(best[1], positive) if best else None


def faithful_ring(segs):
    """Integer rings that stay on this contour. None if that cannot be done safely.

    A self-crossing join can split into more than one simple piece. Every piece
    is kept when, together, they still cover the measured ink.
    """
    raw = _trace(segs)
    if len(raw) < 3:
        return None
    reference_area = abs(_area(raw))
    positive = _area(raw) > 0
    if reference_area < 40 or len(raw) < 4:
        # A notch this small cannot survive a strict area ratio. Keep a valid
        # integer ring on the same curve, or drop a speck that collapsed.
        dust = _orient(_dedup((int(round(x)), int(round(y))) for x, y in raw), positive)
        if len(dust) >= 3 and Polygon(dust).is_valid and (
            len(raw) < 2 or max(LineString(raw).distance(Point(point)) for point in dust) <= 1.6
        ):
            return [dust]
        return []
    reference = LineString(raw)
    float_poly = Polygon(raw)
    if float_poly.is_valid:
        nudged = _nudge_junctions(raw, positive, float_poly.area)
        if nudged:
            return [nudged]
    pts = _cut_revisits(_dedup((int(round(x)), int(round(y))) for x, y in raw))
    if len(pts) < 3:
        return None
    poly = Polygon(pts)
    if not poly.is_valid:
        poly = make_valid(poly)
    polys = [item for item in _polygons(poly) if item.area >= 0.5]
    if not polys:
        return None
    rings = []
    for item in polys:
        ring = _orient(_integer_ring(item), positive)
        if len(ring) < 3:
            if item.area < 4:
                continue
            return None
        if max(reference.distance(Point(point)) for point in ring) > 2.5:
            return None
        rings.append(ring)
    if not rings:
        return None
    covered = sum(Polygon(ring).area for ring in rings)
    if reference_area > 1 and not 0.85 <= covered / reference_area <= 1.15:
        return None
    return rings


def _geometry_pieces(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    if geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
        pieces = []
        for part in geom.geoms:
            pieces.extend(_geometry_pieces(part))
        return pieces
    return []


def bake_true_type_outline(glyph, geometry):
    """Store the compiled TrueType ink as integer lines.

    A cubic that the quadratic step flattens differently from CFF can leave
    TTF and OTF more than 1.6 UPM apart. The TrueType drawing is the one this
    master already compiled; both formats then use that same polygon.
    """
    rings = []
    for poly in _geometry_pieces(geometry):
        ring = _integer_ring(poly)
        if len(ring) >= 3:
            rings.append(_orient(ring, True))
        for hole in poly.interiors:
            hole_poly = Polygon(list(hole.coords))
            if not hole_poly.is_valid:
                hole_poly = make_valid(hole_poly)
            for part in _geometry_pieces(hole_poly):
                hole_ring = _integer_ring(part)
                if len(hole_ring) >= 3:
                    rings.append(_orient(hole_ring, False))
    if not rings:
        raise ValueError(f'{glyph.name}: TrueType outline had no rings')
    _write_lines(glyph, rings)
    glyph.clearComponents()
    return len(rings)


def _write_lines(glyph, rings):
    glyph.clearContours()
    pen = glyph.getPointPen()
    for ring in rings:
        if len(ring) < 3:
            continue
        pen.beginPath()
        for point in ring:
            pen.addPoint(point, segmentType='line', smooth=False)
        pen.endPath()


def _write_cubics(glyph, seg_sets):
    glyph.clearContours()
    pen = glyph.getPointPen()
    for segs in seg_sets:
        if len(segs) < 2:
            continue
        closing = segs[-1]
        pen.beginPath()
        pen.addPoint(segs[0]['p0'], segmentType='curve' if closing['kind'] == 'curve' else 'line', smooth=bool(segs[0].get('smooth0')))
        for index, seg in enumerate(segs):
            if seg['kind'] == 'curve':
                pen.addPoint(seg['c1'], segmentType=None, smooth=False)
                pen.addPoint(seg['c2'], segmentType=None, smooth=False)
            if index < len(segs) - 1:
                pen.addPoint(seg['p1'], segmentType='curve' if seg['kind'] == 'curve' else 'line', smooth=bool(segs[index + 1].get('smooth0')))
        pen.endPath()


def _round_segs(segs):
    rounded = []
    for seg in segs:
        item = {'kind': seg['kind'], 'smooth0': seg.get('smooth0', False)}
        for field in ('p0', 'p1', 'c1', 'c2'):
            if field in seg:
                item[field] = (float(round(seg[field][0])), float(round(seg[field][1])))
        rounded.append(item)
    if not rounded:
        return rounded
    fixed = []
    for index, seg in enumerate(rounded):
        seg = dict(seg)
        seg['p0'] = rounded[index - 1]['p1']
        fixed.append(seg)
    return fixed


def _rounded_valid(seg_sets):
    glyph = Glyph(name='rounded')
    _write_cubics(glyph, [_round_segs(segs) for segs in seg_sets if segs])
    return geometry.inspect(glyph)['valid']


def _resample(seg_sets):
    rings = []
    for segs in seg_sets:
        if not segs:
            continue
        parts = faithful_ring(segs)
        if parts is None:
            return None
        rings.extend(parts)
    return rings


def _recording_contours(glyph, font):
    pen = DecomposingRecordingPen(font)
    glyph.draw(pen)
    contours, current, cursor, start = [], [], None, None
    for op, args in pen.value:
        if op == 'moveTo':
            if current:
                contours.append(current)
            start = args[0]
            cursor = start
            current = []
        elif op == 'lineTo':
            current.append({'kind': 'line', 'p0': cursor, 'p1': args[0], 'smooth0': False})
            cursor = args[0]
        elif op == 'curveTo':
            c1, c2, end = args
            current.append({'kind': 'curve', 'p0': cursor, 'c1': c1, 'c2': c2, 'p1': end, 'smooth0': False})
            cursor = end
        elif op == 'qCurveTo':
            points = list(args)
            on_end, offs, prev = points[-1], points[:-1], cursor
            for index, off in enumerate(offs):
                nxt = on_end if index == len(offs) - 1 else ((off[0] + offs[index + 1][0]) / 2, (off[1] + offs[index + 1][1]) / 2)
                c1 = (prev[0] + 2 / 3 * (off[0] - prev[0]), prev[1] + 2 / 3 * (off[1] - prev[1]))
                c2 = (nxt[0] + 2 / 3 * (off[0] - nxt[0]), nxt[1] + 2 / 3 * (off[1] - nxt[1]))
                current.append({'kind': 'curve', 'p0': prev, 'c1': c1, 'c2': c2, 'p1': nxt, 'smooth0': False})
                prev = nxt
            cursor = on_end
        elif op == 'closePath':
            if current and start is not None and cursor != start:
                current.append({'kind': 'line', 'p0': cursor, 'p1': start, 'smooth0': False})
            if current:
                contours.append(current)
            current, cursor, start = [], None, None
    if current:
        contours.append(current)
    return contours


def compile_checks(font):
    """Outline conversion used for stored masters: no overlap removal."""
    common = dict(useProductionNames=False, removeOverlaps=False, overlapsBackend='pathops', inplace=False)
    ttf = ufo2ft.compileTTF(font, cubicConversionError=0.0002, flattenComponents=True,
                            filters=[DecomposeTransformedComponentsFilter(pre=True)], **common)
    otf = ufo2ft.compileOTF(font, optimizeCFF=0, **common)
    bad = {}
    for label, compiled in (('ttf', ttf), ('otf', otf)):
        glyphs = compiled.getGlyphSet()
        bad[label] = [name for name in compiled.getGlyphOrder() if not geometry.inspect(glyphs[name], glyphs)['valid']]
    return bad


def _departure(original_segs, glyph):
    raw = []
    for segs in original_segs:
        raw.extend(_trace(segs))
    if len(raw) < 2 or not glyph.contours:
        return None
    reference = LineString(_dedup(raw))
    points = [(point.x, point.y) for contour in glyph.contours for point in contour.points if point.segmentType]
    if not points:
        return None
    return round(max(reference.distance(Point(point)) for point in points), 2)


def _round_offsets(font):
    """Component placement is integer. A fractional shift changes how each point rounds."""
    for glyph in font:
        for component in glyph.components:
            xx, yx, xy, yy, x, y = component.transformation
            component.transformation = (xx, yx, xy, yy, float(round(x)), float(round(y)))


def sanitize_font(font):
    """Mutate one stored master. Raises if a contour still will not compile."""
    _round_offsets(font)
    originals = {glyph.name: [read_segments(contour) for contour in glyph.contours] for glyph in font if glyph.contours}
    repaired, decomposed = [], []
    for name, seg_sets in originals.items():
        if _rounded_valid(seg_sets):
            _write_cubics(font[name], [_round_segs(segs) for segs in seg_sets if segs])
            continue
        rings = _resample(seg_sets)
        if rings is None:
            raise ValueError(f'{name}: resampling left the measured curve')
        _write_lines(font[name], rings)
        if not geometry.inspect(font[name])['valid']:
            raise ValueError(f'{name}: resampled contour is still invalid')
        repaired.append(name)
    pending = set()
    for _ in range(3):
        bad = compile_checks(font)
        pending = set(bad['ttf']) | set(bad['otf'])
        if not pending:
            break
        for name in sorted(pending):
            glyph = font[name]
            if glyph.components:
                seg_sets = _recording_contours(glyph, font)
                rings = _resample(seg_sets)
                if rings is None:
                    raise ValueError(f'{name}: transformed component left its drawing')
                glyph.clearComponents()
                _write_lines(glyph, rings)
                decomposed.append(name)
            else:
                seg_sets = originals.get(name) or [read_segments(contour) for contour in glyph.contours]
                rings = _resample(seg_sets)
                if rings is None:
                    raise ValueError(f'{name}: compiled outline left the measured curve')
                _write_lines(glyph, rings)
                repaired.append(name)
            if glyph.contours and not geometry.inspect(glyph)['valid']:
                raise ValueError(f'{name}: cleanup still invalid in the UFO')
    if pending:
        raise ValueError('Compiled contours still invalid: ' + ', '.join(sorted(pending)[:24]))
    tabular = retabulate(font)
    stacking = restack_marks(font)
    drift = {name: _departure(originals[name], font[name]) for name in REVIEW if name in originals}
    return {'repaired_contours': sorted(set(repaired)), 'decomposed': sorted(set(decomposed)), 'drift': drift, 'tabular': tabular, 'stacking': stacking}


def _compiled_gap(ttf, otf, inspect, name, gate):
    true_type = ttf.getGlyphSet()
    postscript = otf.getGlyphSet()
    left = inspect(true_type[name], true_type)
    right = inspect(postscript[name], postscript)
    if not left['valid'] or not right['valid']:
        return None, True
    if left['geometry'].is_empty and right['geometry'].is_empty:
        return 0, False
    distance = left['geometry'].boundary.hausdorff_distance(right['geometry'].boundary)
    # Vertex distance understates a curve edge. Segmentize once the cheap
    # distance is already in the range where the 1.6 gate can still fail.
    if distance > 0.4:
        distance = left['geometry'].boundary.segmentize(2).hausdorff_distance(right['geometry'].boundary.segmentize(2))
    return distance, distance > gate


def _contour_sources(font, name, seen=None):
    seen = seen or set()
    if name in seen or name not in font:
        return set()
    seen.add(name)
    glyph = font[name]
    if glyph.contours:
        return {name}
    found = set()
    for component in glyph.components:
        found |= _contour_sources(font, component.baseGlyph, seen)
    return found


def _scaled(glyph):
    for component in glyph.components:
        xx, yx, xy, yy, _, _ = component.transformation
        if abs(xx - 1) > 1e-3 or abs(yy - 1) > 1e-3 or abs(yx) > 1e-3 or abs(xy) > 1e-3:
            return True
    return False


def snap_compiled_outlines(font, ttf, otf, inspect, gate=1.6):
    """Make TTF and OTF agree without turning accent stacks into outlines.

    A drifting composite keeps its components. The contour sources under it
    are stored as the TrueType polygon, so both formats draw the same lines.
    A scaled figure of those lines is flattened itself: the compiler's scale
    of a dense outline is what was becoming self-crossing.
    """
    bad = []
    for name in ttf.getGlyphOrder():
        _, failed = _compiled_gap(ttf, otf, inspect, name, gate)
        if failed:
            bad.append(name)
    sources = set()
    scaled = []
    for name in bad:
        glyph = font[name]
        if glyph.contours:
            sources.add(name)
        else:
            sources |= _contour_sources(font, name)
            if _scaled(glyph):
                scaled.append(name)
    baked = []
    true_type = ttf.getGlyphSet()
    for name in sorted(sources):
        drawn = inspect(true_type[name], true_type)
        if not drawn['valid'] or drawn['geometry'] is None or drawn['geometry'].is_empty:
            continue
        bake_true_type_outline(font[name], drawn['geometry'])
        baked.append(name)
    for name in scaled:
        drawn = inspect(font[name], font)
        if not drawn['valid'] or drawn['geometry'] is None or drawn['geometry'].is_empty:
            raise ValueError(f'{name}: scaled figure is not a valid outline')
        bake_true_type_outline(font[name], drawn['geometry'])
        baked.append(name)
    return baked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', default='', help='Process paths containing this text')
    parser.add_argument('--tabulate-only', action='store_true', help='Recenter tabular figures without resampling contours')
    parser.add_argument('--restack-only', action='store_true', help='Place marks from this master anchors without resampling contours')
    parser.add_argument('--snap-outlines', action='store_true', help='Bake TTF ink where TTF and OTF disagree by more than 1.6 UPM')
    args = parser.parse_args()
    root = ROOT / 'design/weights-0500/sources'
    paths = sorted(path for path in root.glob('*/*.ufo') if path.is_dir() and '_work' not in path.name and args.only in str(path))
    if not paths:
        raise SystemExit('No masters matched')
    for path in paths:
        font = Font.open(path)
        if args.tabulate_only:
            width = retabulate(font)
            font.save(path, overwrite=True)
            print(path.parent.name, path.name, 'tabular', width, flush=True)
            continue
        if args.restack_only:
            report = restack_marks(font)
            font.save(path, overwrite=True)
            print(path.parent.name, path.name, report, flush=True)
            continue
        if args.snap_outlines:
            from fontTools.ttLib import TTFont
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from tools.release_support import reference_checks
            family, style = path.parent.name, path.stem
            ttf_path = ROOT / 'dist/ttf' / family / f'{family}-{style}.ttf'
            otf_path = ROOT / 'dist/otf' / family / f'{family}-{style}.otf'
            inspect = reference_checks().inspect
            with TTFont(ttf_path) as ttf, TTFont(otf_path) as otf:
                baked = snap_compiled_outlines(font, ttf, otf, inspect)
            if baked:
                font.save(path, overwrite=True)
            print(family, style, 'baked', len(baked), flush=True)
            continue
        report = sanitize_font(font)
        font.save(path, overwrite=True)
        interesting = {name: report['drift'].get(name) for name in ('B', 'M', 'R', 'a', 'g', 'e', 'two', 'three', 'six', 'eight', 'nine') if name in report['drift']}
        print(path.parent.name, path.name, 'repaired', len(report['repaired_contours']), 'decomposed', len(report['decomposed']), 'tabular', report['tabular'], 'drift', interesting, flush=True)


if __name__ == '__main__':
    main()
