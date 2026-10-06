# Full reference cut / 已批准核心的全字符扩展

The owner explicitly accepted Core 01 and requested the remaining characters.
Work continues in PR #10, at the approved reference cut of each family.

`approved-core.json` freezes the accepted 22 glyphs and their source snapshot.
`design/core-01/sources` is immutable history. New editable drawings live in
`sources/<family>-Reference.ufo`, with one GLIF per glyph. A hash/semantic gate
must prevent accidental changes to the approved curves and advances.

## Scope

Complete uppercase/lowercase Latin, digits, punctuation, original supported
Latin extensions, combining marks, symbols and the existing feature repertoire.
`repertoire.json` records the exact 0.301 inventory: 810 encoded codepoints and
945 glyph names. It was extracted from metadata only, never from old outlines.
It is a coverage contract, not a drawing source or a claim to cover all Unicode.

This task extends the **reference cut**, not eight new weights or synthetic
Obliques. Remaining weights need their own later optical design pass; never
fabricate them by expanding this cut. No merge, production replacement, release,
installation or website deployment until the full design is reviewed.

## Drawing approach

New basic letters/digits are individually authored cubic outlines. Reuse is
reserved for meaningful typography: components of accented letters, mark
placement through anchors, repeated punctuation elements, and numeric features.
Composite construction is explicit and editable; it is not presented as hundreds
of independently hand-drawn base alphabets. Each precomposed form must agree with
its decomposed equivalent in real shaping tests.

Primary references for the interchange/layout machinery (not letter shapes):
- https://unifiedfontobject.org/versions/ufo3/glyphs/glif/
- https://glyphsapp.com/learn/diacritics
- https://adobe-type-tools.github.io/afdko/OpenTypeFeatureFileSpecification.html

Build code loads these UFO drawings. Draft helpers never overwrite edited sources
silently. Real-font proofs, source and serialized topology checks, mark positioning,
feature regressions and native/browser acceptance precede the final PR review.

## Completed reference delivery

The remaining existing repertoire is complete in both reference cuts: **810
encoded codepoints / 986 glyphs per family**. All original 945 glyph names are
present; `helper-glyphs.json` explains the 41 additional unencoded companions.
The accepted core remains locked, including its advances and encodings.

Start with [the Chinese visual review and full results](REVIEW.zh-CN.md),
[actual-font overview](proofs/overview.png), [every-glyph atlas](proofs/atlas.md),
and `proofs/review.html` for the separate offline source-vector browser. PNGs
are actual CFF/RAQM renders; HTML vectors are not presented as browser-shaped
text. `qa.json` binds validation to exact source, font and image hashes.

### Isolated build and checks

```sh
python3 -m venv .release-work/full-env
.release-work/full-env/bin/python -m pip install -r design/full-01/requirements.txt
.release-work/full-env/bin/python -m unittest discover -s design/full-01/tests -v
.release-work/full-env/bin/python design/full-01/tools/export_glyphs.py --check-only
.release-work/full-env/bin/python design/full-01/tools/build.py
.release-work/full-env/bin/python design/full-01/tools/check.py
.release-work/full-env/bin/python design/full-01/tools/check_fontbakery.py
.release-work/full-env/bin/python design/full-01/tools/check_reproducibility.py
.release-work/full-env/bin/python design/full-01/tools/proof.py
.release-work/full-env/bin/python -m playwright install chromium
.release-work/full-env/bin/python design/full-01/tools/check_browser.py
# Optional actual macOS verification, process registration only:
swift design/full-01/tools/check_coretext.swift
.release-work/full-env/bin/python design/full-01/tools/record_qa.py
```

After intentional edits to UFO glyphs, run `export_glyphs.py` without
`--check-only` to refresh the derived Glyphs companions, then rebuild and repeat
the gates. It never overwrites the authoritative UFO. Normal construction uses
ufo2ft and the requested family's stored drawings, not the historic skeleton.

Source and compiled contour validity, exact coverage and mapping, mark collision
checks, forced-decomposed shaping under all five stylistic sets, true ligature
caret positions, cross-format geometry and lossless WOFF2 are independent gates.
The pre-existing exact Sigma case-coverage exception is retained explicitly;
FontBakery universal still has warnings and a nonzero raw exit. Technical passes
do not approve the visual quality of every new glyph or create more weights.

Additional primary engineering references:
- https://github.com/googlefonts/ufo2ft (standard compilation and component filters)
- https://github.com/googlefonts/gftools/blob/main/Lib/gftools/fix.py (unhinted scan-control instruction sequence)
- https://www.twardoch.com/download/polishhowto/ogonek.html (joining ogonek design guidance, not imported letter outlines)
