# QA — 0.500 multi-weight family

The gate is the existing release pipeline, extended to 32 styles (96 files). It is not a second, softer pipeline.

## What is checked

- Regular 400 upright, both families, TTF/OTF/WOFF2: every outline, advance and `cmap`/`hmtx`/`GDEF`/`GSUB`/`GPOS` table matches a fresh compile of the hash-locked 0.400 UFO.
- Every other style is compiled from its stored UFO. Coverage stays 986 glyphs / 810 codepoints. OTS, contour validity, encoded shaping, canonical composites and seven ligature carets are checked on all 96 files.
- Forced decomposition (2,964 pairs per file, gate 1.6 UPM) runs on 20 TTF files: every upright, plus Regular Oblique and Black Oblique, per family. The other 12 Oblique TTFs are 10° derivatives of masters that passed that pair set; they get the same encoded-shaping checks plus a fixed sample (`BMRage23689` and é). OTF and WOFF2 of a style must stay within 1.6 UPM of that style’s TTF, and WOFF2 glyf coordinates must match TTF.
- FontBakery universal runs on 64 desktop files (not WOFF2). The only accepted FAIL is the existing Sigma case-mapping finding: U+03A3 without U+03C3. Any other FAIL fails the gate. Warnings are retained. A scoped pass is not a green universal profile.
- Builds must repeat byte-for-byte in a second directory. The specimen loads all 32 WOFF2 files.

Win clip metrics are a shared box, usWinAscent 1606 and usWinDescent 626, written on every style including Regular. 1606 is the measured `head.yMax` of zayJu Black `uni1E50` (O plus a stacked macron and grave) after mark restack; 626 covers yMin −626. Typographic line spacing stays the approved Regular values, so heavier styles can warn that sTypoAscender does not clear Agrave. That warning is kept. FontBakery runs once per family and desktop format so the italic-axis check can see the upright sibling. The only accepted FAIL is still one Sigma finding per file.

`docs/qa/release-0.500.json` is written by `tools/summarize_qa.py` after those commands. The counts below are the scoped run that JSON binds. Do not add an unreviewed sigma to clear the FAIL. Issue #3 stays the coverage follow-up.

## FontBakery is not an all-green universal profile

64 desktop files (TTF and OTF). The scoped gate passed: no unexpected FAIL, ERROR or FATAL. Each file keeps **one** accepted FAIL, `case_mapping` / `missing-case-counterparts`, because U+03A3 is encoded and U+03C3 is not. That is 64 Sigma findings, the same exception as 0.400, not a new Greek glyph.

Warning rows in that run, counted once per file:

| Check | TTF | OTF |
| --- | ---: | ---: |
| soft_hyphen | 32 | 32 |
| math_signs_width | 30 | 30 |
| opentype.gdef_spacing_marks | 28 | 28 |
| contour_count | 32 | 0 |
| unreachable_glyphs | 0 | 32 |
| typoascender_exceeds_Agrave | 6 | 6 |
| overlapping_path_segments | 11 | 0 |

`typoascender_exceeds_Agrave` stays because typographic line spacing is still the approved Regular value while heavier ink is taller. It is on LihuiT Black and Black Oblique, and on zayJu Extrabold, Extrabold Oblique, Black and Black Oblique. `overlapping_path_segments` is a TTF warning, not a pass, on LihuiT Thin, Thin Oblique, Light, Light Oblique and Medium Oblique, and on zayJu Light, Light Oblique, Semibold Oblique, Bold, Bold Oblique and Extrabold Oblique. Full messages stay in the QA JSON.

## Known drawing exceptions

See `docs/design/0.500-weights.md`. `.notdef`, the weight-500 em dash, and zayJu Bold U+238B use explicit constructions because the measured restroke would not keep their counters. Review letters are not in that list.

Joins that doubled back were cut and the contour was resampled onto the same measured curve. On the review letters the new points stay within 1 UPM of that curve. Stored masters compile without overlap removal, because the union step put those knots back. Regular 400 upright still uses the hash-locked compiler, overlap removal included.
