# Source and rights record / 来源与权利边界

## Input

The project owner supplied the local `Lihui-Zixian-Source-v0.300` engineering source and raster design boards, and requested publication in `SheathedSharp/oh-my-font`. A separate working copy was created; the original source, earlier generated fonts, virtual environment and full design boards were not overwritten or uploaded wholesale.

Eleven imported source/build files are listed with their original SHA-256 hashes in `history/source-0.300.sha256.json`. Those original files were re-read after this work and still match the recorded hashes. This verifies those files, not a full forensic snapshot of every item on the owner's computer.

The owner requested the names **LihuiT** and **zayJu**, mapped respectively from Lihui and Zixian. Author attribution remains **zayju**, with the GitHub author URL supplied by the project. That attribution does not independently verify identity, exclusivity or all possible rights in a raster design.

## Outline construction

The imported project constructs its outlines from local geometry code and `src/reference_masters.json`. It does not load an installed font as a drawing source. The display cut uses 19 reference-derived glyphs at selected weights plus reconstructed/derived outlines; the complete character set is not eight independently hand-finished masters.

`history/0.300-design.zh-CN.md` explains the original reference scope and inconsistencies across conceptual raster panels. It is preserved as history, not evidence that every panel is already implemented. `history/0.300-reference-measurements.json` contains reconstruction measurements. The owner-supplied full raster boards remain on the owner's computer. The repository screenshot is instead a new capture of the actual local webfont specimen.

The present changes concern naming, build metadata, checks and the specimen website. They do not claim a new visual redesign of all glyphs. There is no complete Greek, Cyrillic or Han design, variable axis, monospaced branch or separately drawn Italic.

## License status

**No distribution license has been applied to this candidate.** The proposed font license is SIL OFL 1.1, but approval of free commercial use, modification/redistribution, absence of Reserved Font Names and the scope across font sources, tools and design materials remains pending. This document does not grant those permissions.

The original rights note is preserved in `history/0.300-rights.zh-CN.md`; the current root `RIGHTS.zh-CN.md` continues to state the pending status. No new OFL/MIT label is placed over third-party materials or dependencies. No assertion of worldwide exclusivity, independent commercial clearance or zero infringement risk is made.

Build/QA dependencies are installed separately into a local environment and are not included in source imports or a distribution archive. They remain subject to their respective licenses. The standard unhinted scan-control instruction sequence is informed by the primary technical implementation below; it is not glyph-level hinting.

## Primary technical references

- OpenType naming: https://learn.microsoft.com/en-us/typography/opentype/spec/name
- OS/2 metrics and flags: https://learn.microsoft.com/en-us/typography/opentype/spec/os2
- FontTools OS/2 recalculation API: https://fonttools.readthedocs.io/en/latest/ttLib/tables/O_S_2f_2.html
- Unhinted scan control reference: https://github.com/googlefonts/gftools/blob/main/Lib/gftools/fix.py
- FontBakery: https://github.com/fonttools/fontbakery
- OpenType Sanitizer: https://github.com/khaledhosny/ots
- OFL official FAQ and text: https://openfontlicense.org/ofl-faq/ and https://openfontlicense.org/open-font-license-official-text/
