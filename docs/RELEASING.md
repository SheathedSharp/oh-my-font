# Release procedure — approved Regular redesign

Version 0.400 publishes LihuiT Regular and zayJu Regular, 400 upright, in six
TTF/OTF/WOFF2 files. The owner-approved drawing inputs are locked by
`config/approved-reference.json`. Current `build.py` does not use historical
`src/` drawing recipes or synthesize missing weights. Old tags and Releases must
not be overwritten.

## Build and verify exact official files

Use a clean worktree and a dedicated Python environment. A pre-existing output
with unknown/older weights is rejected rather than silently mixed or deleted.

```sh
python -m pip install -r requirements.txt -r requirements-qa.txt
python -m unittest discover -s tests -v
python build.py
python tools/check_candidates.py
python tools/check_fontbakery.py
python tools/check_reproducibility.py
python tools/prepare_site.py
# Serve site/ using a local HTTP server, then:
python tools/check_site.py --browser chromium
# On macOS, optional exact-file native check (no persistent installation):
swift tools/check_coretext.swift
python tools/summarize_qa.py
```

The candidate check compares every official serialized outline and layout table
to a fresh compile of the accepted source, then runs full geometry, OTS, encoding,
feature, forced-decomposition and cross-format checks. FontBakery runs each
family/desktop format separately and retains the precise pre-existing Sigma
case-mapping FAIL and all warnings. A scoped pass is not a green universal profile.

`docs/qa/release-<VERSION>.json` binds checks, browser responses and optional native
results to current source and output hashes. Do not reuse a prior report after
editing source, tools, website assets or version. Preserve OFL, author and source
notices in the repository, font metadata and every archive.

## Integrate and package

Merge approved design and release-integration PRs only after exact-head checks
succeed. Rebuild and verify from the final main commit or prove all input hashes
and outputs remain identical; commit source/docs/QA before packaging.

```sh
python tools/package_release.py
python tools/verify_release.py --directory release --version 0.400 --commit "$(git rev-parse HEAD)"
```

Packaging requires a clean worktree and exact QA hashes. It creates four ZIPs
(TTF, OTF, WOFF2, Website), BUILD-MANIFEST.json, QA.json and SHA256SUMS.txt. Every
archive contains OFL, attribution, authors, FONTLOG, source commit and internal
checksums. Only two Regular font files occur in each archive; no legacy font is
bundled. GitHub's automatic source archive is not an installable font package.

## Publish

Create an annotated version tag at the verified final main commit and push it
without force. Create a draft release with `gh release create --verify-tag --draft`,
upload exactly the seven named assets, verify their names/counts/hashes, then
publish. Never use `--clobber` on public font assets or move a public tag.

Download all seven published assets into a fresh empty directory and run
`tools/verify_release.py` against that directory with the exact tag commit. It
checks external/internal checksums, safe archive paths, exact font identities,
coverage, license metadata and website inventory. Only then report the release
as verified. There is no automatic font installation.

## Deploy the same website artifact

`Publish specimen` deploys the **published Website ZIP**, not a new font build,
to the Cloudflare Pages project `oh-my-font`, serving `https://fonts.zayju.de/`.
The repository's existing `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` secrets
stay in GitHub; never print or embed them. Publication triggers deployment;
manual recovery uses `gh workflow run pages.yml --ref main -f tag=v0.400`.

Verify the workflow succeeded, the public SOURCE.json matches the tag's commit,
font-manifest.json says the current version with two Regular faces, and every
public WOFF2 matches the release hash. Run `tools/check_site.py --url
https://fonts.zayju.de/ --browser chromium` against the live site as well.

## Migration notice

Users should deactivate older LihuiT/zayJu installs before installing 0.400 and
choose TTF OR OTF, not both. New Regular drawings should not be mixed with old
0.301 weights as if they were a consistent family. Further independently designed
weights/italics require separate approval and are not part of this release.
