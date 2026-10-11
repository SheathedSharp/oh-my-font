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
import argparse, itertools, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'design/core-01/tools'))
sys.path.insert(0, str(ROOT / 'design/weights-0500/tools'))
import geometry
import ufo2ft
from fontTools.pens.recordingPen import DecomposingRecordingPen
from ufo2ft.filters.decomposeTransformedComponents import DecomposeTransformedComponentsFilter
from ufoLib2 import Font
from ufoLib2.objects import Glyph
from redraw import read_segments, _sample_segment, _area
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon
from shapely.validation import make_valid

REVIEW = ('A', 'B', 'M', 'R', 'a', 'g', 'e', 'two', 'three', 'six', 'eight', 'nine')


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
    drift = {name: _departure(originals[name], font[name]) for name in REVIEW if name in originals}
    return {'repaired_contours': sorted(set(repaired)), 'decomposed': sorted(set(decomposed)), 'drift': drift}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', default='', help='Process paths containing this text')
    args = parser.parse_args()
    root = ROOT / 'design/weights-0500/sources'
    paths = sorted(path for path in root.glob('*/*.ufo') if path.is_dir() and '_work' not in path.name and args.only in str(path))
    if not paths:
        raise SystemExit('No masters matched')
    for path in paths:
        font = Font.open(path)
        report = sanitize_font(font)
        font.save(path, overwrite=True)
        interesting = {name: report['drift'].get(name) for name in ('B', 'M', 'R', 'a', 'g', 'e', 'two', 'three', 'six', 'eight', 'nine') if name in report['drift']}
        print(path.parent.name, path.name, 'repaired', len(report['repaired_contours']), 'decomposed', len(report['decomposed']), 'drift', interesting, flush=True)


if __name__ == '__main__':
    main()
