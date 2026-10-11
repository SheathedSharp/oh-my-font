# QA — 0.500 multi-weight family

The gate is the existing release pipeline, extended to 32 styles (96 files). It is not a second, softer pipeline.

## What is checked

- Regular 400 upright, both families, TTF/OTF/WOFF2: every outline, advance and `cmap`/`hmtx`/`GDEF`/`GSUB`/`GPOS` table matches a fresh compile of the hash-locked 0.400 UFO.
- Every other style is compiled from its stored UFO. Coverage stays 986 glyphs / 810 codepoints. OTS, contour validity, encoded shaping, canonical composites and seven ligature carets are checked on all 96 files.
- Forced decomposition (2,964 pairs per file, gate 1.6 UPM) runs on 20 TTF files: every upright, plus Regular Oblique and Black Oblique, per family. The other 12 Oblique TTFs are 10° derivatives of masters that passed that pair set; they get the same encoded-shaping checks plus a fixed sample (`BMRage23689` and é). OTF and WOFF2 of a style must stay within 1.6 UPM of that style’s TTF, and WOFF2 glyf coordinates must match TTF.
- FontBakery universal runs on 64 desktop files (not WOFF2). The only accepted FAIL is the existing Sigma case-mapping finding: U+03A3 without U+03C3. Any other FAIL fails the gate. Warnings are retained. A scoped pass is not a green universal profile.
- Builds must repeat byte-for-byte in a second directory. The specimen loads all 32 WOFF2 files.

Win clip metrics are a shared box, usWinAscent 1388 and usWinDescent 626, large enough for every master including Oblique. Typographic line spacing stays the approved Regular values, so heavier styles can warn that sTypoAscender does not clear Agrave. That warning is kept. FontBakery runs once per family and desktop format so the italic-axis check can see the upright sibling. The only accepted FAIL is still one Sigma finding per file.

`docs/qa/release-0.500.json` is written by `tools/summarize_qa.py` after those commands. Do not paste a count into this file until that JSON exists. Do not add an unreviewed sigma to clear the FAIL. Issue #3 stays the coverage follow-up.

## Known drawing exceptions

See `docs/design/0.500-weights.md`. `.notdef`, the weight-500 em dash, and zayJu Bold U+238B use explicit constructions because the measured restroke would not keep their counters. Review letters are not in that list.

Joins that doubled back were cut and the contour was resampled onto the same measured curve. On the review letters the new points stay within 1 UPM of that curve. Stored masters compile without overlap removal, because the union step put those knots back. Regular 400 upright still uses the hash-locked compiler, overlap removal included.
