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
