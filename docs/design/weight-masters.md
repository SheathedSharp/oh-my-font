# Independent weight masters and curve-quality repair

Tracking: #7. Baseline font source: 11095a0 (unchanged at branch base d22dbbb).

## Reproduced defects

- Light n/m/h have flared feet: the counter's lower rounded corners extend above the baseline.
- Light e combines an upper ring and a separate lower stroke; at Thin the pieces do not join.
- R's leg starts above the bowl's lower stroke, leaving a spur inside the counter.
- All compiled outlines are integer-rounded line segments, including CFF.
- Heavier reference-derived zayJu forms are expanded/eroded from one polygon.

## Design boundary

Retain the geometric text/display identities, deliberate open a/g/y forms, coverage,
feature repertoire, metrics unless needed for a repair, OFL and source attribution.
Keep issue #3's coverage work separate. Oblique remains a documented 10-degree
slant of each independently drawn upright master, not a newly drawn italic.

Use sixteen independently editable cubic-outline source masters (two families by
eight weights). A normal build must read exactly its weight's stored outlines,
never expand/erode or interpolate another weight. Drafting/migration helpers are
not production sources and must not overwrite edited masters by default.

Correct defects before composing accents/alternates. Preserve intended corners,
use CFF cubics directly and fontTools cu2qu for TrueType. Geometric, topology,
shaping, sanitizer and renderer checks complement rather than replace optical
review. Do not label all glyphs manually reviewed based on automated checks.

## Technical references

- https://glyphsapp.com/learn/multiple-masters-part-1-setting-up-masters
- https://fonttools.readthedocs.io/en/stable/cu2qu/index.html
- https://shapely.readthedocs.io/en/stable/reference/shapely.buffer.html
- https://simoncozens.github.io/beziers.py/source/beziers.path.html

Glyphs distinguishes drawn masters from computed instances; cu2qu preserves end
curve tangents while approximating within its requested error. Shapely buffers
produce polygons, so more buffer segments alone do not solve vector export.

## Implemented outcome (0.302 candidate)

The production drawing source is now `sources/masters/<family>/<weight>.json`.
`src/masters.py` loads that exact file, and `build.py` preserves cubic CFF paths
and converts TrueType through cu2qu. Historical reference expansion and migration
fitting live only under `tools/drawing/`; normal builds cannot import them.

The first fitting/rounding iterations were rejected when they produced optically
dark counter corners, fractional CFF closure drift or a TrueType fraction spike.
They were repaired at the drawing/export boundary, not hidden by relaxing QA.
An all-format audit additionally exposed merged double-acutes in zayJu 900. That
master received a separate 4 UPM-per-side spacing correction, and actual binary
hashes confirmed no changes to the other 90 font files.

See [the complete results and caveats](../QA-0.302.md),
[before/after proofs](../qa/0.302/index.md) and
[per-weight SVG editing](../../sources/README.md). Each master is independently
editable; the work is not represented as a fresh hand redraw of every glyph or
as a new set of separately drawn italics.

Additional primary implementation references:

- https://fonttools.readthedocs.io/en/latest/ttLib/removeOverlaps.html
- https://shapely.readthedocs.io/en/stable/strtree.html

The curve-preserving overlap pass is for TrueType integer-grid cleanup, not
synthetic weight generation. STRtree accelerates the same sampled nearest-segment
distance checks; it does not relax the cross-format error threshold.
