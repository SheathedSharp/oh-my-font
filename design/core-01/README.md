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

## Review the delivered first draft

Start with [中文视觉验收说明与对照图](REVIEW.zh-CN.md).

- `proofs/overview.png`: actual CFF-rendered core and word samples.
- `proofs/capitals.png`: B/M/R at large size.
- `proofs/before-after.png`: explicitly labeled comparison with rejected PR #8.
- `proofs/review.html`: self-contained UFO-vector review, with outline/handle toggles and unsupported-character blocking.
- `sources/*.ufo`: authoritative per-glyph GLIF design files.
- `sources/*.glyphs`: synchronized Glyphs-format editing companions, not a claim that the GUI was used.

### Isolated tooling

```sh
python3 -m venv .release-work/core-env
.release-work/core-env/bin/python -m pip install -r design/core-01/requirements.txt
.release-work/core-env/bin/python design/core-01/tools/build.py
.release-work/core-env/bin/python design/core-01/tools/check.py
.release-work/core-env/bin/python -m playwright install chromium
.release-work/core-env/bin/python design/core-01/tools/check_browser.py
# macOS process-only native check, never installation:
swift design/core-01/tools/check_coretext.swift
```

Edit the UFO glyphs individually in a compatible editor. When intentionally
synchronizing the companion after edits, use `build.py --export-glyphs`; it
replaces only the derived Glyphs companions, never the UFO drawing sources.
`proof.py` renders those drawings without inventing missing letters. Proofs and
`qa.json` must be refreshed after any source change. Do not run the production
build to manufacture additional letters or weights for this design study.

OFL, author zayju and the original repository attribution are carried into the
study metadata. Binary proof fonts are local build outputs and are not committed,
published, installed, merged or substituted for the production families.
