# 0.302 junction and independent-weight verification

**Development candidate for PR #8 / issue #7; not a published release.**
The original 0.301 release, public website and installed fonts are unchanged.
The exact input and output hashes are in [the machine-readable QA record](qa/release-0.302.json).

## Changes verified

Both families now have eight separately editable upright outline masters under
`sources/masters/`, at weights 100, 300, 400, 500, 600, 700, 800 and 900. Each stores
its own complete 945-glyph / 810-codepoint inventory, cubic control points,
spacing and anchors. A normal build reads that weight's file and cannot synthesize
a missing weight from another master. Historical drafting/reference-buffer code
has been moved out of `src/`; production import isolation is tested.

The light-cut repairs remove the unintended n/m/h baseline flares, make e one
connected shape with its intended counter, rebuild D/P/R stem/bowl junctions and
remove R's counter spur. Related composed/alternate forms were generated from the
corrected bases during the migration and then stored independently. Intended open
a/g/y forms and angular zayJu display details are not rounded indiscriminately.

CFF now retains real cubic curves. TrueType uses cu2qu at 0.25 UPM before integer
quantization and a standard curve-preserving overlap pass. A 1/64 UPM binary
coordinate grid prevents fractional CFF closure drift. The emitted files—not just
in-memory drawings—are inspected for invalid contours and degenerate geometry.

## A defect found by the full-format audit

The first conversion audit found that zayJu 900's double-acute strokes could merge
after TrueType integer rounding while remaining separate in CFF. The largest
sampled boundary discrepancy was 49.738690 UPM. The gate was **not** relaxed.

Only the zayJu 900 master was edited: the two acute contours were moved outward
by 4 UPM each in `uni030B`, `uni02DD`, `uni0150`, `uni0151`, `uni0170` and `uni0171`.
Centers, advance widths and anchors remain unchanged. Serialized TTF/CFF tests
now require the intended separate components in both upright and Oblique.

Hash comparison before/after this final drawing edit showed **only six changed
files**: zayJu Black and BlackOblique in TTF, OTF and WOFF2. **The other 90 files
were byte-identical.** This is an actual per-weight isolation check, not merely a
directory layout claim. See the `weight-isolation` section of the QA record.

## Results for the final candidate

| Check | Observed result |
| --- | --- |
| Regression tests | 15 passed, including baseline reproduction, source isolation, SVG roundtrip, real cubic/quadratic export, serialized closure/rounding and double-acute separation |
| Stored masters | 16 complete, independently editable upright masters; 15,120 stored glyph drawings |
| Source geometry | All 32 upright/Oblique styles × 945 glyphs = 30,240 inspections; no invalid-source or explicit junction-regression failures |
| Serialized geometry | All 96 files × 945 glyphs = 90,720 inspections; no invalid/degenerate contour findings |
| Structure, metadata and OTS | 96/96 candidates passed; OFL, author and original-source metadata retained |
| HarfBuzz | 1,440 fixed shaping assertions passed across all 96 files |
| TTF/CFF comparison | All 30,240 glyph pairs passed; largest sampled boundary distance 1.178935 UPM, below the unchanged 1.6 UPM gate |
| WOFF2 | All 32 faces preserve their TTF glyph coordinates, flags, advances and mapping losslessly |
| macOS CoreText | 64 exact desktop files, 512 sample lines, no fallback; process-only registration and cleanup |
| Browser | All 32 exact WOFF2 faces loaded in Chrome 154.0.8037.98; 1440/900/390 px layouts, controls, missing-font handling and reduced-motion checks passed; no unexpected page/request errors |
| Reproducibility | Two full builds into separate directories on the same machine produced identical bytes for all 96 files |

The conversion distance is a **dense sampled boundary comparison**, not an
analytic maximum-error proof. Its 1.6 UPM gate includes integer rounding and
overlap cleanup, unlike the pre-quantization cu2qu 0.25 UPM setting. The indexed
segment-distance implementation is regression-tested against the original dense
reference calculation; it does not substitute nearest sampled endpoints.

The QA record checks all recorded candidate, outline, conversion, browser,
CoreText, proof and rebuild hashes against the same final files. It rejects
missing or stale results. Release packaging also requires the new outline and
conversion gates. GitHub Actions repeats the build and core gates on Linux;
consult the PR's check status for the exact commit rather than treating this
local macOS record as proof of a later CI run.

## FontBakery: scoped pass, not an all-green universal profile

All four family/desktop-format universal groups were run in full. The existing
strict scoped gate passed, with **no unexpected FAIL/ERROR findings**. The raw
universal profiles still exit with status 1: there are **64 existing Sigma
case-mapping FAIL results**, one per desktop font, because U+03A3 is present and
U+03C3 is absent. No fabricated glyph or broader exception was added.

There are also **256 WARN check results**. Their categories and per-group counts
match 0.301: TTF groups report alt_caron, contour_count, ligature_carets,
math_signs_width and soft_hyphen; CFF groups report the latter three. These remain
visible in the machine record, not dismissed as universally harmless. Issue #3
continues to track the unrelated coverage and typographic-polish work.

## Optical evidence and limits

[Open the proof index](qa/0.302/index.md): both families at all eight weights in
upright and Oblique; before/after light-cut comparisons; the Black double-acute
repair. Images use the actual compiled font files, and the proof manifest records
their hashes. All four all-weight sheets, both light comparisons and the
double-acute sheet were visually inspected during this development round.

These are **migrated and optically corrected original drawings**, not a claim that
every glyph of both families was hand-drawn from scratch. Straight segments remain
where intentional or where a conservative draft fit was rejected. Each Oblique is
still a documented 10-degree transform of its own weight's upright master, not a
separately drawn italic. Automated all-glyph coverage does not constitute manual
optical approval of every glyph at every size.

No persistent font installation, Windows-native test, full-language expansion,
variable-font design, publication, tag, merge or deployment is asserted here.
Maintainer optical approval and the existing issue #3 scope remain distinct from
this completed junction-development and verification round.
