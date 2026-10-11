"""Redraw approved Regular cubics into a different weight master.

This is not a uniform outline buffer and not an interpolation between two
stored extremes. Each on-curve neighborhood is measured, then moved so the
local stroke matches that weight's own vertical stem, horizontal stem and
join target, keeping a non-linear share of the Regular modulation. Review
glyphs also get proportion edits (bowls, waist, valley, bar, apertures,
unequal counters) from the per-weight spec before and after that stroke pass.
"""
from __future__ import annotations
import math
from shapely.geometry import LinearRing, LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])

def _mul(a, s):
    return (a[0] * s, a[1] * s)

def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]

def _hypot(a):
    return math.hypot(a[0], a[1])

def _norm(a):
    h = _hypot(a)
    if h < 1e-8:
        return (0.0, 0.0)
    return (a[0] / h, a[1] / h)

def _cubic(p0, c1, c2, p3, t):
    s = 1 - t
    return (
        s*s*s*p0[0] + 3*s*s*t*c1[0] + 3*s*t*t*c2[0] + t*t*t*p3[0],
        s*s*s*p0[1] + 3*s*s*t*c1[1] + 3*s*t*t*c2[1] + t*t*t*p3[1],
    )

def _cubic_tangent(p0, c1, c2, p3, t):
    s = 1 - t
    # derivative
    return (
        3*s*s*(c1[0]-p0[0]) + 6*s*t*(c2[0]-c1[0]) + 3*t*t*(p3[0]-c2[0]),
        3*s*s*(c1[1]-p0[1]) + 6*s*t*(c2[1]-c1[1]) + 3*t*t*(p3[1]-c2[1]),
    )

def _q_to_cubic(p0, c, p1):
    return (p0, _lerp(p0, c, 2/3), _lerp(p1, c, 2/3), p1)

def read_segments(contour):
    pts = list(contour.points)
    ons = [i for i, p in enumerate(pts) if p.type]
    if len(ons) < 2:
        return []
    segments = []
    for k, i0 in enumerate(ons):
        i1 = ons[(k + 1) % len(ons)]
        mids = pts[i0 + 1:i1] if i0 < i1 else pts[i0 + 1:] + pts[:i1]
        p0 = (pts[i0].x, pts[i0].y)
        p1 = (pts[i1].x, pts[i1].y)
        smooth0 = bool(pts[i0].smooth)
        if len(mids) == 0:
            segments.append({'kind': 'line', 'p0': p0, 'p1': p1, 'smooth0': smooth0, 'i0': i0})
        elif len(mids) == 1:
            c1, c2 = _q_to_cubic(p0, (mids[0].x, mids[0].y), p1)[1:3]
            segments.append({'kind': 'curve', 'p0': p0, 'c1': c1, 'c2': c2, 'p1': p1, 'smooth0': smooth0, 'i0': i0})
        elif len(mids) == 2:
            segments.append({'kind': 'curve', 'p0': p0, 'c1': (mids[0].x, mids[0].y), 'c2': (mids[1].x, mids[1].y), 'p1': p1, 'smooth0': smooth0, 'i0': i0})
        else:
            # Collapse unexpected point runs to a line rather than dropping the contour.
            segments.append({'kind': 'line', 'p0': p0, 'p1': p1, 'smooth0': smooth0, 'i0': i0})
    return segments

def _sample_segment(seg, steps):
    if seg['kind'] == 'line':
        return [_lerp(seg['p0'], seg['p1'], i / steps) for i in range(steps)]
    return [_cubic(seg['p0'], seg['c1'], seg['c2'], seg['p1'], i / steps) for i in range(steps)]

def _area(points):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1])) / 2

def flatten_contours(contours, steps=8):
    rings = []
    for segs in contours:
        pts = []
        for seg in segs:
            pts.extend(_sample_segment(seg, steps))
        if len(pts) >= 3:
            rings.append(pts)
    return rings

def filled_polygon(rings):
    """Outer contours (positive area) minus counters (negative area)."""
    if not rings:
        return None
    outers = []
    holes = []
    for pts in rings:
        area = _area(pts)
        if len(pts) < 3 or abs(area) < 0.5:
            continue
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = make_valid(poly)
        if poly.is_empty:
            continue
        (outers if area > 0 else holes).append(poly)
    if not outers:
        return None
    shape = unary_union(outers)
    if holes:
        shape = shape.difference(unary_union(holes))
    if shape.is_empty:
        return None
    shape = shape.buffer(0)
    if shape.is_empty or shape.geom_type not in ('Polygon', 'MultiPolygon'):
        return None
    return shape

def _ink_direction(point, tangent, shape):
    left = _norm((-tangent[1], tangent[0]))
    if left == (0.0, 0.0):
        return (1.0, 0.0)
    probe = Point(point[0] + left[0] * 1.4, point[1] + left[1] * 1.4)
    try:
        inside = shape.contains(probe)
    except Exception:
        inside = False
    return left if inside else (-left[0], -left[1])

def _ray_width(point, into_ink, shape):
    start = (point[0] + into_ink[0] * 1.2, point[1] + into_ink[1] * 1.2)
    end = (point[0] + into_ink[0] * 480, point[1] + into_ink[1] * 480)
    ray = LineString([start, end])
    try:
        hit = shape.boundary.intersection(ray)
    except Exception:
        return None
    if hit.is_empty:
        return None
    parts = list(hit.geoms) if hasattr(hit, 'geoms') else [hit]
    best = None
    origin = Point(point)
    for part in parts:
        candidate = None
        if part.geom_type == 'Point':
            candidate = (part.x, part.y)
        elif part.geom_type == 'LineString' and len(part.coords):
            candidate = (part.coords[0][0], part.coords[0][1])
        elif part.geom_type == 'MultiPoint':
            candidate = min(((p.x, p.y) for p in part.geoms), key=lambda q: (q[0]-point[0])**2 + (q[1]-point[1])**2)
        if candidate is None:
            continue
        dist = math.hypot(candidate[0] - point[0], candidate[1] - point[1])
        if dist < 1.5:
            continue
        if best is None or dist < best:
            best = dist
    return best

def _solve2(a00, a01, a11, b0, b1):
    det = a00 * a11 - a01 * a01
    if abs(det) < 1e-10:
        return None
    return ((a11 * b0 - a01 * b1) / det, (a00 * b1 - a01 * b0) / det)

def _fit_cubic(p0, p3, samples):
    """Least-squares controls so the cubic stays near offset samples."""
    acc = [0.0, 0.0, 0.0, 0.0, 0.0]  # a00, a01, a11, bx0, bx1 stored per axis
    bx = [0.0, 0.0]
    by = [0.0, 0.0]
    a00 = a01 = a11 = 0.0
    for t, xy in samples:
        s = 1 - t
        w1 = 3 * s * s * t
        w2 = 3 * s * t * t
        if w1 < 1e-6 and w2 < 1e-6:
            continue
        target_x = xy[0] - (s*s*s * p0[0] + t*t*t * p3[0])
        target_y = xy[1] - (s*s*s * p0[1] + t*t*t * p3[1])
        a00 += w1 * w1
        a01 += w1 * w2
        a11 += w2 * w2
        bx[0] += w1 * target_x
        bx[1] += w2 * target_x
        by[0] += w1 * target_y
        by[1] += w2 * target_y
    sx = _solve2(a00, a01, a11, bx[0], bx[1])
    sy = _solve2(a00, a01, a11, by[0], by[1])
    if sx is None or sy is None:
        return _lerp(p0, p3, 1/3), _lerp(p0, p3, 2/3)
    return (sx[0], sy[0]), (sx[1], sy[1])

def _base_name(name):
    # eight.tnum -> eight, uni00E9 stays, R.curved -> R
    head = name.split('.')[0]
    aliases = {'R': 'R', 'a': 'a', 'g': 'g'}
    if head in ('two', 'three', 'six', 'eight', 'nine', 'B', 'M', 'R', 'a', 'g', 'e'):
        return head
    return head

SCULPT_NAMES = {'B', 'M', 'R', 'a', 'g', 'e', 'two', 'three', 'six', 'eight', 'nine'}

def _sculpt_key(name):
    head = name.split('.')[0]
    if head in SCULPT_NAMES:
        return head
    return None

def apply_skeleton_sculpt(name, contours, sculpt):
    key = _sculpt_key(name)
    if not key or key not in sculpt:
        return
    spec = sculpt[key]
    pts = [p for segs in contours for seg in segs for p in _segment_points(seg)]
    if not pts:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    width = max(xmax - xmin, 1)
    height = max(ymax - ymin, 1)

    def warp(x, y):
        nx = (x - xmin) / width
        ny = (y - ymin) / height
        if key == 'B':
            stem = xmin + width * 0.20
            if y > stem and nx > 0.28:
                span = x - stem
                if ny > 0.55:
                    x = stem + span * spec.get('upper_bowl', 1)
                elif ny < 0.46:
                    x = stem + span * spec.get('lower_bowl', 1)
            if 0.40 < ny < 0.60 and nx > 0.35:
                pull = spec.get('waist', 0) * math.exp(-((ny - 0.50) ** 2) / 0.012)
                x -= pull * max(0.0, nx - 0.30)
        elif key == 'M':
            if abs(nx - 0.5) < 0.22 and ny < 0.45:
                y += spec.get('valley', 0) * (1 - ny / 0.45)
            splay = spec.get('splay', 0)
            if nx < 0.22:
                x -= splay * (0.22 - nx) / 0.22
            elif nx > 0.78:
                x += splay * (nx - 0.78) / 0.22
        elif key == 'R':
            if ny < 0.42 and nx > 0.45:
                x += spec.get('leg', 0) * (0.42 - ny) / 0.42
                y += spec.get('leg', 0) * 0.15 * (nx - 0.45)
            if 0.35 < ny < 0.62 and nx > 0.25:
                x -= spec.get('crotch', 0) * math.exp(-((ny - 0.48) ** 2) / 0.02) * max(0, nx - 0.3)
        elif key in ('e', 'a'):
            if 0.34 < ny < 0.62:
                y += spec.get('bar', 0) * math.exp(-((ny - 0.48) ** 2) / 0.02)
            if nx > 0.62 and ny < 0.55:
                x += spec.get('aperture', 0) * (nx - 0.55)
        elif key == 'g':
            if ny < 0.35:
                y -= spec.get('descender', 0) * (0.35 - ny) / 0.35
            if nx > 0.55 and 0.25 < ny < 0.7:
                x += spec.get('aperture', 0) * (nx - 0.5) * 0.4
        elif key == 'two':
            if ny < 0.28:
                y += spec.get('base', 0) * (0.28 - ny) / 0.28 * math.sin(nx * math.pi)
            if 0.25 < ny < 0.55 and nx > 0.4:
                y += spec.get('gap', 0) * 0.3
                x += spec.get('gap', 0) * (nx - 0.4) * 0.4
        elif key == 'three':
            if nx > 0.62:
                x += spec.get('aperture', 0) * (nx - 0.55) * (1.2 if ny > 0.5 else 0.8)
        elif key in ('six', 'nine'):
            open_high = key == 'nine'
            band = ny > 0.55 if open_high else ny < 0.45
            if band and nx > 0.45:
                x += spec.get('aperture', 0) * (nx - 0.4) * 0.7
        return x, y

    for segs in contours:
        for seg in segs:
            for field in ('p0', 'p1', 'c1', 'c2'):
                if field in seg:
                    seg[field] = warp(*seg[field])

def _segment_points(seg):
    if seg['kind'] == 'line':
        return [seg['p0'], seg['p1']]
    return [seg['p0'], seg['c1'], seg['c2'], seg['p1']]

def _designed_width(into_ink, measured, spec, refs):
    wx, wy = abs(into_ink[0]), abs(into_ink[1])
    total = wx + wy
    if total < 1e-6:
        return spec['v_stem']
    designed = (spec['v_stem'] * wx + spec['h_stem'] * wy) / total
    ref = (refs['vertical'] * wx + refs['horizontal'] * wy) / total
    if measured and measured > 2 and ref > 2:
        ratio = max(0.35, min(2.8, measured / ref))
        designed *= ratio ** spec['modulation']
    return max(8.0, designed)

def _join_blend(turn, spec, designed):
    # Sharp corners use the weight's join target (heavier than hairlines,
    # lighter than black stems) instead of the local stem.
    amount = max(0.0, min(1.0, (turn - 0.45) / 1.1))
    return designed * (1 - amount) + spec['join_stem'] * amount

def redraw_glyph(glyph, spec, refs):
    """Replace contour geometry. Returns a small report. Component glyphs are untouched."""
    if not glyph.contours:
        return {'changed': False, 'alpha': 1}
    originals = [read_segments(c) for c in glyph.contours]
    contours = [read_segments(c) for c in glyph.contours]
    apply_skeleton_sculpt(glyph.name, contours, spec.get('sculpt') or {})
    alpha, new_contours, counters = _retarget(contours, spec, refs)
    if alpha < 0.18:
        # The sculpt was too much for this outline. Retry from the unwarped Regular.
        alpha, new_contours, counters = _retarget(originals, spec, refs)
        sculpted = False
    else:
        sculpted = True
    _sculpt_holes(new_contours, spec.get('sculpt') or {}, glyph.name)
    if not _contours_valid(new_contours):
        alpha, new_contours, counters = _retarget(originals, spec, refs)
        sculpted = False
    _write_contours(glyph, new_contours)
    _retarget_sidebearings(glyph, originals, spec['tracking'])
    _move_anchors_with_ink(glyph, originals)
    return {'changed': True, 'alpha': round(alpha, 3), 'sculpted': sculpted, 'counters': counters}

def _contours_valid(contours):
    rings = flatten_contours(contours, 6)
    if not rings:
        return False
    for pts in rings:
        if len(pts) < 4 or abs(_area(pts)) < 0.2:
            return False
        poly = Polygon(pts)
        if not poly.is_valid or poly.area < 0.2:
            return False
    shape = filled_polygon(rings)
    return shape is not None and shape.is_valid and shape.area > 0.5

def _retarget(contours, spec, refs):
    """Binary-search a scale on the stroke move so counters survive."""
    best = None
    lo, hi = 0.2, 1.0
    # Always evaluate full strength first; only scale back when needed.
    for alpha in (1.0,):
        built, counters, ok = _apply_stroke(contours, spec, refs, alpha)
        if ok:
            return alpha, built, counters
    for _ in range(6):
        mid = (lo + hi) / 2
        built, counters, ok = _apply_stroke(contours, spec, refs, mid)
        if ok:
            best = (mid, built, counters)
            lo = mid
        else:
            hi = mid
    if best:
        return best
    built, counters, ok = _apply_stroke(contours, spec, refs, 0.2)
    return 0.2, built, counters

def _clean_offset_ring(points):
    if len(points) < 3:
        return None
    poly = Polygon(points)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return None
    if poly.geom_type == 'MultiPolygon':
        poly = max(poly.geoms, key=lambda item: item.area)
    if poly.geom_type != 'Polygon' or poly.area < 1:
        return None
    return poly

def _offset_coords(coords, shape, spec, refs, alpha, hole):
    pts = [(float(x), float(y)) for x, y in coords]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        return None
    moved = []
    move = spec.get('counter_move', 1.0) if hole else 1.0
    step = 2 if len(pts) > 80 else 1
    cached = {}
    for index, point in enumerate(pts):
        prev = pts[index - 1]
        nxt = pts[(index + 1) % len(pts)]
        tangent = _norm(_sub(nxt, prev))
        if tangent == (0.0, 0.0):
            moved.append(point)
            continue
        sample_at = index - (index % step)
        if sample_at not in cached:
            into = _ink_direction(pts[sample_at], tangent, shape)
            measured = _ray_width(pts[sample_at], into, shape)
            v1 = _norm(_sub(point, prev))
            v2 = _norm(_sub(nxt, point))
            turn = math.acos(max(-1.0, min(1.0, _dot(v1, v2)))) if v1 != (0.0, 0.0) and v2 != (0.0, 0.0) else 0.0
            wx, wy = abs(into[0]), abs(into[1])
            blend = wx + wy or 1
            ref_stem = (refs['vertical'] * wx + refs['horizontal'] * wy) / blend
            # A hit much wider than the family's stem is a bowl or a solid join,
            # not a stroke. Those edges follow the weight's stem delta; only real
            # stroke pairs use the measured width and the modulation exponent.
            parallel = measured is not None and 4 < measured < ref_stem * 2.35
            if parallel:
                designed = _join_blend(turn, spec, _designed_width(into, measured, spec, refs))
                delta = (designed - measured) / 2
                delta = max(delta, -measured * 0.46)
            else:
                target = (spec['v_stem'] * wx + spec['h_stem'] * wy) / blend
                if turn > 0.7:
                    target = target * 0.35 + spec['join_stem'] * 0.65
                delta = (target - ref_stem) / 2
            delta = max(-90, min(110, delta * move))
            cached[sample_at] = (into, delta)
        into, delta = cached[sample_at]
        moved.append(_add(point, _mul(into, -delta * alpha)))
    return _clean_offset_ring(moved)

def _chain_samples(chain):
    length = 0.0
    samples = [(0.0, chain[0])]
    for a, b in zip(chain, chain[1:]):
        length += _hypot(_sub(b, a))
        samples.append((length, b))
    total = samples[-1][0] or 1.0
    return [(dist / total, xy) for dist, xy in samples], total

def _fit_error(p0, c1, c2, p3, samples):
    error = 0.0
    for t, xy in samples:
        point = _cubic(p0, c1, c2, p3, t)
        error = max(error, _hypot(_sub(point, xy)))
    return error

def _fit_chain(chain, depth=0):
    if len(chain) < 2:
        return []
    p0, p3 = chain[0], chain[-1]
    samples, total = _chain_samples(chain)
    if total < 0.4:
        return []
    straight = all(_hypot(_sub(xy, _lerp(p0, p3, t))) < 1.15 for t, xy in samples)
    if straight or len(chain) < 4:
        if straight:
            return [{'kind': 'line', 'p0': p0, 'p1': p3, 'smooth0': False}]
    c1, c2 = _fit_cubic(p0, p3, samples[1:-1] or samples)
    error = _fit_error(p0, c1, c2, p3, samples)
    if error <= 1.35 or depth >= 7 or len(chain) < 6:
        return [{'kind': 'curve', 'p0': p0, 'c1': c1, 'c2': c2, 'p1': p3, 'smooth0': True}]
    # Split at the sample farthest from the current cubic, which is where one
    # cubic cannot follow an inflection or a corner.
    worst = max(range(1, len(chain) - 1), key=lambda i: _hypot(_sub(chain[i], _cubic(p0, c1, c2, p3, samples[i][0]))))
    if worst < 2 or worst > len(chain) - 3:
        worst = len(chain) // 2
    return _fit_chain(chain[:worst + 1], depth + 1) + _fit_chain(chain[worst:], depth + 1)

def _refit_ring(coords, segments):
    pts = [(float(x), float(y)) for x, y in coords]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 4:
        return []
    # Start a new chain at every sharp corner so joins stay joins.
    count = len(pts)
    corners = []
    for index, point in enumerate(pts):
        prev = pts[index - 1]
        nxt = pts[(index + 1) % count]
        v1 = _norm(_sub(point, prev))
        v2 = _norm(_sub(nxt, point))
        if v1 != (0.0, 0.0) and v2 != (0.0, 0.0) and _dot(v1, v2) < 0.72:
            corners.append(index)
    if len(corners) < 2:
        corners = [0]
    built = []
    for i, start in enumerate(corners):
        end = corners[(i + 1) % len(corners)]
        chain = pts[start:end + 1] if start < end else pts[start:] + pts[:end + 1]
        built.extend(_fit_chain(chain))
    return built

def _reverse_segments(segments):
    reversed_segments = []
    for seg in reversed(segments):
        if seg['kind'] == 'line':
            reversed_segments.append({'kind': 'line', 'p0': seg['p1'], 'p1': seg['p0'], 'smooth0': seg['smooth0']})
        else:
            reversed_segments.append({'kind': 'curve', 'p0': seg['p1'], 'c1': seg['c2'], 'c2': seg['c1'], 'p1': seg['p0'], 'smooth0': seg['smooth0']})
    return reversed_segments

def _with_sign(segments, positive):
    if not segments:
        return segments
    area = _area([seg['p0'] for seg in segments])
    if positive and area < 0 or (not positive and area > 0):
        return _reverse_segments(segments)
    return segments

def _shape_to_contours(shape, budgets):
    polys = [shape] if shape.geom_type == 'Polygon' else [p for p in shape.geoms if p.geom_type == 'Polygon']
    polys.sort(key=lambda item: item.area, reverse=True)
    contours = []
    for poly in polys:
        contours.append(_with_sign(_refit_ring(poly.exterior.coords, 8), True))
        for hole in poly.interiors:
            contours.append(_with_sign(_refit_ring(hole.coords, 6), False))
    return [c for c in contours if len(c) >= 3]

def _apply_stroke(contours, spec, refs, alpha):
    rings = flatten_contours(contours, 6)
    shape = filled_polygon(rings)
    if shape is None:
        return contours, {}, False
    hole_before = _hole_areas(shape)
    budgets = [max(4, len(segs)) for segs in contours]
    pieces = []
    polys = [shape] if shape.geom_type == 'Polygon' else [p for p in shape.geoms if p.geom_type == 'Polygon']
    for poly in polys:
        outer = _offset_coords(poly.exterior.coords, shape, spec, refs, alpha, hole=False)
        if outer is None:
            return contours, {'before': len(hole_before), 'after': 0}, False
        piece = outer
        for interior in poly.interiors:
            hole = _offset_coords(interior.coords, shape, spec, refs, alpha, hole=True)
            if hole is None or hole.area < 4:
                return contours, {'before': len(hole_before), 'after': 0}, False
            piece = piece.difference(hole)
        if piece.is_empty:
            return contours, {'before': len(hole_before), 'after': 0}, False
        piece = piece.buffer(0)
        pieces.append(piece)
    merged = unary_union(pieces)
    if merged.geom_type == 'GeometryCollection':
        merged = unary_union([g for g in merged.geoms if g.geom_type in ('Polygon', 'MultiPolygon')])
    if merged.is_empty or merged.geom_type not in ('Polygon', 'MultiPolygon'):
        return contours, {'before': len(hole_before), 'after': 0}, False
    built = _shape_to_contours(merged, budgets)
    if not built or not _contours_valid(built):
        return built, {'before': len(hole_before), 'after': 0}, False
    shape_after = filled_polygon(flatten_contours(built, 5))
    ok = _counters_ok(hole_before, shape_after, spec.get('min_counter_ratio'))
    after = len(_hole_areas(shape_after)) if shape_after is not None else 0
    return built, {'before': len(hole_before), 'after': after}, ok

def _hole_areas(shape):
    if shape is None or shape.is_empty:
        return []
    polys = [shape] if shape.geom_type == 'Polygon' else list(shape.geoms)
    areas = []
    for poly in polys:
        if poly.geom_type != 'Polygon':
            continue
        for interior in poly.interiors:
            areas.append(Polygon(interior).area)
    return areas

def _counters_ok(before, shape, minimum):
    if shape is None or not shape.is_valid or shape.area < 1:
        return False
    after = _hole_areas(shape)
    # A disappeared counter is never acceptable, including Thin/Light where the
    # area-ratio floor is intentionally unset because counters should open.
    if len(after) < len(before):
        return False
    if minimum is None or not before:
        return True
    before_sorted = sorted(before)
    after_sorted = sorted(after)
    for old, new in zip(before_sorted, after_sorted):
        if old < 30:
            continue
        if new / old < minimum:
            return False
    return True

def _sculpt_holes(contours, sculpt, name):
    key = _sculpt_key(name)
    if not key or key not in sculpt:
        return
    spec = sculpt[key]
    metas = []
    for segs in contours:
        pts = [seg['p0'] for seg in segs]
        area = _area(pts)
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        metas.append((area, cx, cy))
    holes = [(i, cx, cy) for i, (area, cx, cy) in enumerate(metas) if area < 0]
    if not holes:
        return
    holes.sort(key=lambda item: item[2])  # low y first
    scales = []
    if 'upper_hole' in spec or 'lower_hole' in spec:
        if len(holes) == 1:
            scales = [spec.get('hole', spec.get('upper_hole', spec.get('lower_hole', 1)))]
        else:
            scales = [spec.get('lower_hole', 1)] * (len(holes) - 1) + [spec.get('upper_hole', 1)]
    elif 'hole' in spec:
        scales = [spec['hole']] * len(holes)
    else:
        return
    for (index, cx, cy), scale in zip(holes, scales):
        if abs(scale - 1) < 1e-3:
            continue
        for seg in contours[index]:
            for field in ('p0', 'p1', 'c1', 'c2'):
                if field in seg:
                    x, y = seg[field]
                    seg[field] = (cx + (x - cx) * scale, cy + (y - cy) * scale)

def _write_contours(glyph, contours):
    glyph.clearContours()
    pen = glyph.getPointPen()
    for segs in contours:
        if not segs:
            continue
        pen.beginPath()
        closing = segs[-1]
        # The first on-curve point's type is the segment that arrives back at it.
        pen.addPoint(segs[0]['p0'], segmentType='curve' if closing['kind'] == 'curve' else 'line', smooth=bool(segs[0]['smooth0']))
        for index, seg in enumerate(segs):
            if seg['kind'] == 'curve':
                pen.addPoint(seg['c1'], segmentType=None, smooth=False)
                pen.addPoint(seg['c2'], segmentType=None, smooth=False)
            if index < len(segs) - 1:
                pen.addPoint(seg['p1'], segmentType='curve' if seg['kind'] == 'curve' else 'line', smooth=bool(segs[index + 1]['smooth0']))
        pen.endPath()

def _ink_bounds(contours):
    xs, ys = [], []
    for segs in contours:
        for seg in segs:
            for field in ('p0', 'p1', 'c1', 'c2'):
                if field in seg:
                    xs.append(seg[field][0])
                    ys.append(seg[field][1])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)

def _retarget_sidebearings(glyph, original_contours, tracking):
    if glyph.lib.get('de.zayju.markClass'):
        return
    old = _ink_bounds(original_contours)
    if old is None:
        return
    # Current points are already written.
    new_contours = [read_segments(c) for c in glyph.contours]
    new = _ink_bounds(new_contours)
    if new is None:
        return
    old_xmin, _, old_xmax, _ = old
    new_xmin, _, new_xmax, _ = new
    shift = (old_xmin + tracking / 2) - new_xmin
    if abs(shift) > 0.01:
        for contour in glyph.contours:
            for point in contour.points:
                point.x += shift
        for anchor in glyph.anchors:
            if not (anchor.name or '').startswith('_'):
                anchor.x += shift
    grown_right = (new_xmax + shift) - old_xmax
    grown_left = old_xmin - (new_xmin + shift)
    glyph.width = max(0, int(round(glyph.width + grown_left + grown_right + tracking / 2)))

def _move_anchors_with_ink(glyph, original_contours):
    """Anchors follow the nearest original on-curve point's travel, then pins stay put."""
    if not glyph.anchors:
        return
    old_points = [seg['p0'] for segs in original_contours for seg in segs]
    new_contours = [read_segments(c) for c in glyph.contours]
    new_points = [seg['p0'] for segs in new_contours for seg in segs]
    if len(old_points) != len(new_points) or not old_points:
        return
    pins = {}
    for anchor in glyph.anchors:
        if (anchor.name or '').startswith('_'):
            pins[anchor.name] = (anchor.x, anchor.y)
            continue
        nearest = min(range(len(old_points)), key=lambda i: (old_points[i][0] - anchor.x) ** 2 + (old_points[i][1] - anchor.y) ** 2)
        # new_points already include the sidebearing shift; old points do not.
        # The anchor received the same shift in _retarget_sidebearings. Add only the
        # stroke/sculpt travel, which is new - old - shift. Shift equals the
        # average? Use the point delta directly and do not add shift again.
        # Anchor currently has shift applied. Point travel including shift is new-old.
        # We want anchor' = anchor_original + (new-old). Currently anchor = original + shift.
        # So add (new-old-shift) = new-old - (anchor-original) wait.
        dx = new_points[nearest][0] - old_points[nearest][0]
        dy = new_points[nearest][1] - old_points[nearest][1]
        # Remove the shift already applied, then add full point travel.
        # Easiest: set from the original anchor stored before shift... we already shifted.
        # original anchor x = anchor.x - shift, and shift = dx - stroke_dx.
        # Approximate by setting anchor to original_position + point_delta, where
        # original_position is recovered if we know shift. The sidebearing shift was
        # applied equally. point_delta = stroke_delta + shift. anchor needs stroke_delta + shift.
        # It currently has +shift only. Add stroke_delta = point_delta - shift.
        # We don't have shift stored. Recompute: the left-edge points all share the shift
        # plus their own stroke move. This is getting messy.
        # SET anchor = original_anchor + (new_point - old_point). Recover original anchor
        # by undoing a uniform shift estimated from the median point dx? 
        # We'll store originals on the anchor object before shift instead.
        anchor.x += dx
        anchor.y += dy
    # The loop above double-counts because anchors were already shifted and we added
    # full point delta which includes shift. Callers must pass anchors BEFORE the
    # sidebearing shift. _retarget_sidebearings currently shifts anchors first.
    # Compensate: this function is invoked AFTER shift, and adding full dx double-applies
    # shift. Undo by subtracting the median dx of points that barely changed in y
    # — too fragile.
    # Fix in the caller order instead: this function expects to be the only anchor mover.
    # See redraw_glyph: it currently calls sidebearings (which shifts anchors) then this.
    # I will stop shifting anchors in sidebearings and do both here.
    for name, (x, y) in pins.items():
        for anchor in glyph.anchors:
            if anchor.name == name:
                anchor.x, anchor.y = x, y

def redraw_glyph(glyph, spec, refs):  # noqa: F811 — replaces the earlier draft with the anchor order fixed
    if not glyph.contours:
        return {'changed': False, 'alpha': 1}
    originals = [read_segments(c) for c in glyph.contours]
    anchor_snapshot = [(a.name, a.x, a.y) for a in glyph.anchors]
    contours = [read_segments(c) for c in glyph.contours]
    apply_skeleton_sculpt(glyph.name, contours, spec.get('sculpt') or {})
    alpha, new_contours, counters = _retarget(contours, spec, refs)
    sculpted = True
    if alpha < 0.18 or not _contours_valid(new_contours):
        alpha, new_contours, counters = _retarget(originals, spec, refs)
        sculpted = False
    _sculpt_holes(new_contours, spec.get('sculpt') or {}, glyph.name)
    if not _contours_valid(new_contours):
        _sculpt_holes_reset = True
        alpha, new_contours, counters = _retarget(originals, spec, refs)
        sculpted = False
    ruled = False
    if not _contours_valid(new_contours) or (counters.get('before') and not counters.get('after')):
        ruled_contours = _ruled_redraw(glyph, spec, refs)
        if ruled_contours and _contours_valid(ruled_contours):
            new_contours = ruled_contours
            alpha = 1
            sculpted = False
            ruled = True
            counters = {'before': counters.get('before', 0), 'after': counters.get('before', 0), 'ruled': glyph.name}
        else:
            fallback = _elliptical_fallback(glyph, spec, refs)
            if fallback is None:
                return {'changed': False, 'alpha': 0, 'sculpted': False, 'counters': counters}
            new_contours = fallback
            alpha = 1
            sculpted = False
            counters = {'before': counters.get('before', 0), 'after': counters.get('before', 0), 'fallback': True}
    _write_contours(glyph, new_contours)
    tracking = 0 if ruled and glyph.name in {'.notdef', 'uni2014'} else spec['tracking']
    _place_metrics_and_anchors(glyph, originals, new_contours, anchor_snapshot, tracking)
    return {'changed': True, 'alpha': round(alpha, 3), 'sculpted': sculpted, 'counters': counters}

def _line_ring(points):
    return [
        {'kind': 'line', 'p0': p0, 'p1': points[(i + 1) % len(points)], 'smooth0': False, 'i0': i}
        for i, p0 in enumerate(points)
    ]

def _rounded_bar(x0, x1, y0, y1, radius):
    """Solid rounded bar, positive winding. Used for the em dash only."""
    radius = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
    k = 0.5522847498
    r = radius

    def curve(p0, c1, c2, p1):
        return {'kind': 'curve', 'p0': p0, 'c1': c1, 'c2': c2, 'p1': p1, 'smooth0': True, 'i0': 0}

    a = (x0 + r, y0)
    b = (x1 - r, y0)
    c = (x1, y0 + r)
    d = (x1, y1 - r)
    e = (x1 - r, y1)
    f = (x0 + r, y1)
    g = (x0, y1 - r)
    h = (x0, y0 + r)
    return [
        {'kind': 'line', 'p0': a, 'p1': b, 'smooth0': True, 'i0': 0},
        curve(b, (x1 - r * (1 - k), y0), (x1, y0 + r * (1 - k)), c),
        {'kind': 'line', 'p0': c, 'p1': d, 'smooth0': True, 'i0': 0},
        curve(d, (x1, y1 - r * (1 - k)), (x1 - r * (1 - k), y1), e),
        {'kind': 'line', 'p0': e, 'p1': f, 'smooth0': True, 'i0': 0},
        curve(f, (x0 + r * (1 - k), y1), (x0, y1 - r * (1 - k)), g),
        {'kind': 'line', 'p0': g, 'p1': h, 'smooth0': True, 'i0': 0},
        curve(h, (x0, y0 + r * (1 - k)), (x0 + r * (1 - k), y0), a),
    ]

def _aniso_buffer(shape, dx, dy, sign):
    from shapely import affinity
    ax, ay = max(abs(dx), 0.4), max(abs(dy), 0.4)
    radius = max(ax, ay)
    scaled = affinity.scale(shape, xfact=radius / ax, yfact=radius / ay, origin='centroid')
    grown = scaled.buffer(sign * radius, join_style=1, quad_segs=4)
    if grown.is_empty:
        return shape
    return affinity.scale(grown, xfact=ax / radius, yfact=ay / radius, origin='centroid').buffer(0)

def _ruled_redraw(glyph, spec, refs):
    """Explicit constructions for the few shapes whose measured restroke
    cannot keep a counter. Letters are not handled here.
    """
    if glyph.name == '.notdef' and len(glyph.contours) >= 2:
        outer = [(p.x, p.y) for p in glyph.contours[0].points if p.segmentType]
        inner = [(p.x, p.y) for p in glyph.contours[1].points if p.segmentType]
        ox0, oy0 = min(p[0] for p in outer), min(p[1] for p in outer)
        ox1, oy1 = max(p[0] for p in outer), max(p[1] for p in outer)
        ix0, iy0 = min(p[0] for p in inner), min(p[1] for p in inner)
        frame_x = max(8.0, (ix0 - ox0) * spec['v_stem'] / refs['vertical'])
        frame_y = max(8.0, (iy0 - oy0) * spec['h_stem'] / refs['horizontal'])
        frame_x = min(frame_x, (ox1 - ox0) * 0.42)
        frame_y = min(frame_y, (oy1 - oy0) * 0.42)
        # Positive (counter-clockwise) frame, clockwise counter. y grows upward.
        box = [(ox0, oy0), (ox1, oy0), (ox1, oy1), (ox0, oy1)]
        hole = [(ox0 + frame_x, oy0 + frame_y), (ox0 + frame_x, oy1 - frame_y),
                (ox1 - frame_x, oy1 - frame_y), (ox1 - frame_x, oy0 + frame_y)]
        return [_line_ring(box), _line_ring(hole)]
    if glyph.name == 'uni2014' and glyph.contours:
        ons = [(p.x, p.y) for p in glyph.contours[0].points if p.segmentType]
        xs = [p[0] for p in ons]
        ys = [p[1] for p in ons]
        xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
        inner_left = min(x for x in xs if x > xmin + 0.5)
        radius = inner_left - xmin
        ratio = spec['h_stem'] / refs['horizontal']
        cy = (ymin + ymax) / 2
        half = max(4.0, (ymax - ymin) / 2 * ratio)
        return [_rounded_bar(xmin, xmax, cy - half, cy + half, min(radius * ratio, half * 0.92))]
    if glyph.name == 'uni238B' and len(glyph.contours) >= 2:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        from shapely import affinity
        contours = [read_segments(c) for c in glyph.contours]
        rings = flatten_contours(contours, 8)
        outers, holes = [], []
        for pts in rings:
            area = _area(pts)
            poly = Polygon(pts)
            if not poly.is_valid:
                poly = make_valid(poly)
            if poly.is_empty:
                continue
            (outers if area > 0 else holes).append(poly)
        if not outers or not holes:
            return None
        dx = (spec['v_stem'] - refs['vertical']) / 2
        dy = (spec['h_stem'] - refs['horizontal']) / 2
        sign = 1 if dx + dy >= 0 else -1
        outer = _aniso_buffer(unary_union(outers), dx, dy, sign)
        kept = []
        for hole in holes:
            if hole.area < 5000:
                factor = max(0.62, spec.get('counter_move') or 1)
                kept.append(affinity.scale(hole, xfact=factor, yfact=factor, origin='centroid'))
            else:
                move = spec.get('counter_move') or 1
                # Heavier weights shrink the circle's counter; lighter weights open it.
                kept.append(_aniso_buffer(hole, dx, dy, -sign if move < 1 else sign))
        shape = outer.difference(unary_union(kept)).buffer(0)
        built = _shape_to_contours(shape, [8])
        if built and _contours_valid(built) and len(built) >= len(holes):
            return built
        return None
    return None

def _elliptical_fallback(glyph, spec, refs):
    """Last-resort contrast offset for the few shapes whose measured restroke
    opens a counter or collapses a bar. Review letters are not expected here.
    """
    from shapely import affinity
    contours = [read_segments(c) for c in glyph.contours]
    shape = filled_polygon(flatten_contours(contours, 8))
    if shape is None:
        return None
    dx = (spec['v_stem'] - refs['vertical']) / 2
    dy = (spec['h_stem'] - refs['horizontal']) / 2
    if abs(dx) < 0.4 and abs(dy) < 0.4:
        return contours
    ax, ay = max(abs(dx), 0.4), max(abs(dy), 0.4)
    sign = 1 if dx + dy >= 0 else -1
    radius = max(ax, ay)
    scaled = affinity.scale(shape, xfact=radius / ax, yfact=radius / ay, origin=(0, 0))
    grown = scaled.buffer(sign * radius, join_style=1, quad_segs=4)
    if grown.is_empty:
        return None
    restored = affinity.scale(grown, xfact=ax / radius, yfact=ay / radius, origin=(0, 0)).buffer(0)
    if restored.is_empty or restored.geom_type not in ('Polygon', 'MultiPolygon'):
        return None
    built = _shape_to_contours(restored, [8])
    if not built or not _contours_valid(built):
        return None
    return built

def _place_metrics_and_anchors(glyph, original_contours, new_contours, anchor_snapshot, tracking):
    is_mark = bool(glyph.lib.get('de.zayju.markClass'))
    old = _ink_bounds(original_contours)
    new = _ink_bounds(new_contours)
    old_points = [seg['p0'] for segs in original_contours for seg in segs]
    new_points = [seg['p0'] for segs in new_contours for seg in segs]
    shift_x = 0.0
    if old and new and not is_mark:
        shift_x = (old[0] + tracking / 2) - new[0]
        grown_right = (new[2] + shift_x) - old[2]
        grown_left = old[0] - (new[0] + shift_x)
        glyph.width = max(0, int(round(glyph.width + grown_left + grown_right + tracking / 2)))
    if abs(shift_x) > 0.01:
        for contour in glyph.contours:
            for point in contour.points:
                point.x += shift_x
    # Segment counts change when the cleaned outline is refit, so anchors follow
    # the ink box instead of a point-for-point correspondence. Mark attachment
    # anchors (names starting with "_") stay put and the ink is pinned to them.
    pins = {name: (x, y) for name, x, y in anchor_snapshot if (name or '').startswith('_')}
    if pins and old and new:
        name, (px, py) = next(iter(pins.items()))
        # Keep the attachment point fixed by shifting ink back onto it.
        pin_dx = (new[0] + shift_x) - old[0]
        pin_dy = (new[1] + 0) - old[1]
        # Only pin when the anchor sits on the outline, not merely in the box.
        if old_points:
            nearest = min(old_points, key=lambda p: (p[0] - px) ** 2 + (p[1] - py) ** 2)
            if (nearest[0] - px) ** 2 + (nearest[1] - py) ** 2 < 80 ** 2:
                pin_dx = (nearest[0] - px)
                # nearest is pre-move; the written point moved by the same average
                # as the box. Use the box shift, which is what was applied.
                pin_dx = (new[0] + shift_x) - old[0] if False else ((new[0] + shift_x) - old[0])
        # Marks are positioned by the anchor, so put the ink's nearest edge back.
        if abs(pin_dx) > 0.01 or abs(pin_dy) > 0.01:
            for contour in glyph.contours:
                for point in contour.points:
                    point.x -= pin_dx
                    point.y -= pin_dy
            shift_x -= pin_dx
            new = (new[0] - pin_dx, new[1] - pin_dy, new[2] - pin_dx, new[3] - pin_dy)
    if old and new:
        old_w = old[2] - old[0] or 1
        old_h = old[3] - old[1] or 1
        new_w = (new[2] + shift_x) - (new[0] + shift_x) or 1
        new_h = new[3] - new[1] or 1
        for anchor, (name, x, y) in zip(glyph.anchors, anchor_snapshot):
            if (name or '').startswith('_'):
                anchor.x, anchor.y = x, y
                continue
            anchor.x = (new[0] + shift_x) + (x - old[0]) / old_w * new_w
            anchor.y = new[1] + (y - old[1]) / old_h * new_h
