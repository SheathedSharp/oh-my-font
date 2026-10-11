# Release procedure — 0.500 multi-weight family

Version 0.500 publishes 32 styles: LihuiT and zayJu, weights 100, 300, 400, 500, 600, 700, 800, 900, each upright and as a 10° Oblique. Regular 400 upright is compiled from the hash-locked 0.400 UFO (`config/approved-reference.json`). Every other style is compiled from a stored master under `design/weights-0500/sources`. `build.py` does not import `src/outlines.py` and does not synthesize a missing weight.

Do not move or overwrite tags **v0.301** or **v0.400**, and do not replace their Release assets. Do not merge the rejected draft PR #8.

Technical CI is not visual approval. Tag v0.500 only after a human has reviewed the weight ladder, especially B, M, R, a, g, e and digits 2/3/6/8/9, upright and Oblique, for both families.

## Build and verify

Use a clean worktree. An output directory that already contains an unknown filename (anything outside the 96 expected files) is rejected rather than deleted.

```sh
python -m pip install -r requirements.txt -r requirements-qa.txt
python -m unittest discover -s tests -v
python build.py
python tools/check_candidates.py
python tools/check_fontbakery.py
python tools/check_reproducibility.py
python tools/prepare_site.py
# Serve site/ over local HTTP, then:
python tools/check_site.py --browser chromium
# On macOS, optional exact-file native check:
swift tools/check_coretext.swift
python tools/summarize_qa.py
```

`docs/qa/release-0.500.json` binds those results to the current source and output hashes. Re-run it after any hashed input changes. The scoped FontBakery gate accepts only the existing Sigma case-mapping FAIL (U+03A3 without U+03C3), once per desktop file. Warnings remain in the report.

## Package, after the commit is the one you will tag

```sh
python tools/package_release.py
python tools/verify_release.py --directory release --version 0.500 --commit "$(git rev-parse HEAD)"
```

Packaging needs a clean worktree and a QA report whose input hashes match that build. It writes four ZIPs (TTF, OTF, WOFF2, Website), `BUILD-MANIFEST.json`, `QA.json` and `SHA256SUMS.txt`. Each archive contains 32 font files of one format (the Website archive contains the 32 WOFF2s), plus OFL and attribution.

## Publish — only after merge to main and visual approval

From the verified main commit, not from an unreviewed side branch:

```sh
git checkout main
git pull origin main
# Confirm this commit is the one whose hashes verify_release.py accepted.
git tag -a v0.500 -m "LihuiT and zayJu 0.500 — first multi-weight redesign"
git push origin v0.500
gh release create v0.500 --verify-tag --draft --title "v0.500 — first multi-weight redesign" --notes-file docs/releases/0.500-notes.md
gh release upload v0.500 release/LihuiT-zayJu-v0.500-TTF.zip release/LihuiT-zayJu-v0.500-OTF.zip release/LihuiT-zayJu-v0.500-WOFF2.zip release/LihuiT-zayJu-v0.500-Website.zip release/BUILD-MANIFEST.json release/QA.json release/SHA256SUMS.txt
# Confirm seven assets, names and hashes, then:
gh release edit v0.500 --draft=false --prerelease=false
```

Never use `--clobber` against v0.301 or v0.400 assets. Never force-move those tags.

Download the seven published assets into an empty directory and run `tools/verify_release.py` against that directory with the tag commit. The site at fonts.zayju.de updates only when the published Website ZIP is deployed (`gh workflow run pages.yml --ref main -f tag=v0.500`). Until that release exists, v0.400 remains the public download.
