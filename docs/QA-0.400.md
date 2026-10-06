# 0.400 official release verification

Release scope: **LihuiT Regular + zayJu Regular, weight 400 upright**, in TTF,
CFF OTF and WOFF2. Each face has 810 encoded codepoints and 986 glyphs. The owner
approved the complete redesign in PR #10 and explicitly authorized publication.
No historic 0.301 faces or unapproved synthetic weights/Obliques are bundled.

## Exact approved design, official identity

`config/approved-reference.json` locks the accepted source snapshot from
`4640e2b38bc20b72e4f5584113208fa819b5adc9`. The production compiler uses those UFOs
and the accepted reference compiler, not historical `src/` geometry recipes.

Promotion changes official family/style/PostScript names, release version and
description only. Build-time checks compare all outlines/advances before and
after promotion. The exact saved release files are independently compared to a
fresh compile of the accepted drawings: **every glyph and the cmap, hmtx, GDEF,
GSUB and GPOS tables must be identical in geometry/meaning**. CFF internal font
names are updated without changing charstring drawings. Unicode naming tables
are retained without adding obsolete Macintosh name records.

## Final candidate checks

- 16 release regression tests passed: scope, rejected old output, approval locks,
  official naming, license/source retention, Unicode naming and safe checksums.
- 1,972 source glyphs and 5,916 serialized official glyphs checked; no invalid
  contour findings. All six outputs match the accepted drawings and layout.
- 6/6 OpenType Sanitizer and structural checks passed.
- 4,740 encoded nonblank character checks, 126 feature regressions and 2,964
  ordinary normalization comparisons passed.
- 17,784 forced-decomposition/feature comparisons passed. Precomposed cmap
  entries are removed only in memory so normalization cannot conceal a broken
  mark anchor; default and ss01–ss05 compare actual positioned outlines/advances.
- All 1,972 TTF/CFF glyph pairs passed the unchanged 1.6 UPM sampled-distance
  gate; the observed maximum was 0.982662 UPM. This is a sampled inspection, not
  an analytic maximum-error proof. Both WOFF2s preserve their TTF glyph data.
- Two full builds into independent directories produced identical bytes for all
  six font files on the same machine and toolchain.
- macOS CoreText resolved four exact desktop files, 48 multilingual sample lines
  and 3,160 encoded mappings without missing glyphs or fallback; process-only
  registration, no persistent installation and no Windows-native claim.
- Chrome loaded exactly two Regular WOFF2s; their response hashes matched the
  release. The hero used the actual custom zayJu face. 1440/900/390 px layouts,
  family/features/reset/dark mode, missing-file behavior and reduced motion passed.
  No unapproved weights or Obliques are offered by the website controls.

`docs/qa/release-0.400.json` binds all results to the current source, official font
and website hashes. The release workflow repeats build, exact-candidate checks,
FontBakery, reproducibility and Chromium verification. Consult the PR's exact
head checks for CI, rather than treating a local result as evidence for a later
commit. Design proofs and prior full-reference checks remain in `design/full-01/`.

## FontBakery is not misrepresented as all-green

All four family/desktop-format universal profiles were run separately. The strict
scoped gate passed with no unexpected FAIL/ERROR. Raw profiles retain **four
existing Sigma case-coverage FAIL results** because U+03A3 exists and U+03C3 does
not. That exact exception is not expanded to mask new failures.

There are **eight WARN check results**: contour_count and soft_hyphen for the
TTFs; soft_hyphen and caron.right reachability for CFF. Full messages and raw exits
remain in QA.json. These findings are not called universally harmless; broader
coverage/polish remains tracked in issue #3. Soft hyphen retains its codepoint
but has no default ink and zero advance.

## Publication verification and migration

Packaging refuses a dirty worktree, old/unknown font files, stale source/font
hashes or incomplete gates. Four ZIPs plus BUILD-MANIFEST.json, QA.json and
SHA256SUMS.txt carry exact source-commit data and internal/external checksums.
The draft assets are verified before publication; all published assets are
freshly downloaded and verified again. The public website deploys that exact
Website ZIP and is checked for its version, source commit and WOFF2 byte hashes.

The existing v0.301 tag/assets remain unchanged. Deactivate old installed
LihuiT/zayJu versions before installing 0.400, and choose TTF OR OTF, not both.
No other weights, italics, full Greek/Cyrillic/Han, variable or monospaced family
are included in this release. OFL, author zayju and original-source attribution
remain in every font and archive.
