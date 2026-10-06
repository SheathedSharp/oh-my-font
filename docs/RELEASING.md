# Release procedure

## Source and verification

Work on a PR, keep the original input project intact, and record the version in `VERSION` (OpenType form such as `0.301`). Font names, copyright/source URL and full OFL metadata are built from the checked-in source. Never replace the official OFL body with custom attribution restrictions.

```sh
python -m pip install -r requirements.txt -r requirements-qa.txt
python -m unittest discover -s tests -v
python build.py
python tools/check_outlines.py
python tools/check_conversion.py
python tools/check_candidates.py
python tools/check_fontbakery.py
python tools/prepare_site.py
# Start a local server for site/, then:
python tools/check_site.py
# Native macOS, before installing an overlapping font identity:
swift tools/check_coretext.swift
```

`check_outlines.py` examines all source styles and serialized font glyphs; `check_conversion.py` compares all TTF/CFF glyphs and verifies lossless WOFF2 outlines. The latter includes integer-grid error and is not the same bound as the pre-quantization cu2qu setting. Run actual optical proofs with `tools/proof_junctions.py` and review the changes.

`check_candidates.py` validates full copyright/source/OFL name-table metadata, OTS and 15 fixed HarfBuzz assertions for every format/face. `check_fontbakery.py` retains all raw results and nonzero profile exits and fails on unreviewed failures. The current precisely scoped exception and all warning categories are recorded in QA-0.302.md and issue #3; QA-0.301.md remains the first-release history. A scoped gate pass is not a full-profile pass.

Optional macOS installed-font acceptance: install TTF only in a new release-specific user font folder without overwriting existing identities, then run `swift tools/check_installed_macos.swift`. That check resolves fonts from an independent process and round-trips RTF using AppKit. Do not describe process-only registration as installation. Inspect actual specimens; document remaining untested applications and scripts.

```sh
python tools/summarize_qa.py
# Commit the exact source, QA and docs, review and merge the PR.
python tools/package_release.py
```

The QA summary binds outline, conversion, browser and available native results to the exact current source/font hashes. Packaging refuses missing/stale geometry or cross-format gates, a dirty worktree, or any changed source/font hash. It makes TTF, OTF, WOFF2 and Website ZIPs, all carrying OFL, attribution, author, FONTLOG and source-commit information. Font binaries are Release attachments, not committed source. Keep `release/` and `.release-work/` ignored.

## Publish

Verify main contains the reviewed source tree. Create an annotated tag at that exact commit, push it without force, create a draft Release, upload the seven explicitly named assets, verify the archive contents and SHA-256 hashes, then publish. Do not overwrite an already public tag or assets silently; make a new version for changed fonts.

After publishing, download every asset into a fresh directory, verify the external and internal checksums and confirm the manifest source commit matches the tag. Only then close the first-release delivery issue; keep genuinely deferred quality work open.

## Website

The Cloudflare Pages project `oh-my-font` (Direct Upload) serves `https://fonts.zayju.de/` through a proxied `CNAME fonts` to `oh-my-font.pages.dev`. `Publish specimen` runs on published Releases and can be manually dispatched with a published `tag`. It downloads and verifies the **released Website ZIP**, extracts it safely and deploys that exact artifact to Cloudflare Pages with Wrangler. It does not rebuild fonts on an uncontrolled newer source revision. Deployment requires the repository secrets `CLOUDFLARE_API_TOKEN` (Account · Cloudflare Pages · Edit) and `CLOUDFLARE_ACCOUNT_ID`.

```sh
gh workflow run pages.yml --ref main -f tag=v0.301
```

Verify the public root, OFL.txt, ATTRIBUTION.txt, SOURCE.json and all WOFF2 responses, and run `tools/check_site.py --url https://fonts.zayju.de/` against the deployed site. The repository uses only minimal per-job permissions and pinned action commits; no credentials are embedded in packages or the website.
