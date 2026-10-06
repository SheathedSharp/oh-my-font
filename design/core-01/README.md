# Core study 01 — 风格重绘，等待视觉验收

Status: **in development / not approved / not a release**.

The owner rejected PR #8's visual result: too mechanical, insufficient character,
especially B and M. This independent branch starts from main, not the rejected
master set. It leaves production fonts, VERSION and the website untouched.

## Exact scope

Only **B M R a g e 2 3 6 8 9** for each family, in one reference cut. No remaining
characters, additional weights, synthetic Obliques or release packages. Approval
of these drawings must precede letter-by-letter expansion.

LihuiT direction: warm humanist curves, unequal bowls, open counter spaces,
softened junctions and a quiet calligraphic rhythm suitable for longer reading.

zayJu direction: more expressive, swelling ribbon-like strokes, forward motion,
fluid waists and individually sculpted terminals rather than rounded rectangles.
The two families must be judged separately.

## Drawing and engineering boundary

Each glyph is a new, individually authored cubic Bézier outline, not a tracing,
a buffer of the old glyph, a rotated counterpart, a skeleton stroke expansion,
or an AI image masquerading as a font. Sources use editable UFO3 / GLIF records;
a Glyphs-format companion and per-glyph SVG proof will be supplied. No proprietary
GUI is claimed to have been operated. Programs compile and inspect the drawn
outlines; they do not decide the letter shape from geometric primitives.

The review will show B/M/R at large sizes, a/g/e and numerals, and only words
that the small supported repertoire can actually render. Missing letters are
explicitly unsupported, never supplied by invisible font fallback.

Technical validation establishes that drawings survive font export. It does not
establish personality, visual approval, suitability for a full text family, or
future multi-weight quality. The owner makes the visual acceptance decision.

## Primary technical references

- Glyphs, Drawing good paths: https://glyphsapp.com/learn/drawing-good-paths
- UFO3 / GLIF specification: https://unifiedfontobject.org/versions/ufo3/glyphs/glif/
- glyphsLib conversion implementation: https://github.com/googlefonts/glyphsLib

These inform curve construction, editable interchange and validation, not the
letter designs. No third-party font outlines are imported. Existing project OFL
and author/source attribution remain in force.
