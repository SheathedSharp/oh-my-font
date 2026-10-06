# Changelog

## 0.400 — approved complete redesign

- Publish the owner-approved LihuiT Regular and zayJu Regular, 400 upright only.
- New individually authored base outlines plus editable accent/feature components: 810 codepoints and 986 glyphs per face.
- Preserve the accepted core and all approved final curves, advances, anchors and OpenType layout; official names/version only.
- Fix accented stylistic-set behavior, ogonek joins, OE export differences and Command-sign interior artifacts; retain 21 features and seven ligature caret records.
- Replace the production build and website inventory so no legacy or synthetic weight is included.
- Keep 0.301 as an unchanged historical release. Deactivate old installed versions before installing this redesign; choose TTF OR OTF, not both.
- Other weights/Obliques are not released. The precisely documented Sigma coverage failure and FontBakery warnings remain visible.


## 0.301 — first public OFL release

- Rename Lihui to LihuiT and Zixian to zayJu in source, font metadata and output names; retain author zayju.
- Repair code-page metadata, legacy regular flags, underline consistency, STAT linking and unhinted scan control.
- Add exact-candidate OTS, HarfBuzz, CoreText and browser verification with documented remaining FontBakery findings.
- Add responsive real-WOFF2 specimen with family/style controls, OpenType features, glyph coverage, dark mode and failure handling.
- Apply owner-approved OFL-1.1 with original-source attribution, no Reserved Font Names and no extra artwork-credit restriction.
- Package exact verified desktop/web fonts and deploy the checksum-verified specimen.
- Verify real macOS user installation and AppKit RTF round-trip; disclose remaining universal-profile findings in issue #3.

## 0.300 — owner-supplied engineering baseline

- Reference-led reconstruction and paired text/display cuts.
- Historical design and rights notes retained in docs/history.
