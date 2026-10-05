# LihuiT & zayJu

**Two voices. One bright idea.** A paired geometric sans-serif project by **zayju**.

[简体中文](README.zh-CN.md) · [Release preparation](https://github.com/SheathedSharp/oh-my-font/issues/1) · [Candidate verification](docs/QA-0.301.md)

![Actual local specimen website, rendered with candidate WOFF2 files](docs/images/specimen-preview.png)

**Status: 0.301 local release candidate. No commercially licensed font release is published yet.** Distribution-license approval and final design/application acceptance are pending. The screenshot is from the real local website; it is not an online deployment or a downloadable font package.

## The pair

| Family | Role | Previous project name |
| --- | --- | --- |
| **LihuiT** | Text and interface; more generous spacing and distinguishable default I/l | Lihui |
| **zayJu** | Display; wide proportions, open a/g and separated y strokes | Zixian |

The family spelling is case-sensitive in project files: **LihuiT / zayJu**. Author attribution remains **zayju**.

Each family has eight static weights (100, 300, 400, 500, 600, 700, 800, 900), upright and 10° Oblique: 32 styles in total. Each style builds as TTF, CFF OTF and WOFF2, producing 96 local files. Each face has 945 glyphs and 810 Unicode code points. These are not variable or monospaced fonts and contain no Han glyphs. Oblique is not a separately drawn Italic. See [scope and known issues](docs/QA-0.301.md).

## Build locally

Python 3.10+ is required. Build dependencies are pinned in `requirements.txt`.

```sh
python3 build-local.py
```

The launcher creates a project-local `.venv` and invokes `build.py`. The platform convenience launchers are also retained. With an existing environment:

```sh
python -m pip install -r requirements.txt
python build.py
# A smaller preview build:
python build.py --families zayJu --weights 700 --styles upright
```

Outputs are under `dist/{ttf,otf,woff2}/{LihuiT,zayJu}/`. Nothing is installed into the operating system. TTF and OTF represent the same identities; choose one format when eventually installing, not both.

## Interactive local specimen

After a complete build:

```sh
python tools/prepare_site.py
python -m http.server 8136 --bind 127.0.0.1 --directory site
```

Open `http://127.0.0.1:8136/` on that computer. The site uses the exact local WOFF2 files, not system-font substitutes. It includes editable text, all weights and Oblique, size/tracking controls, OpenType feature switches, dark mode, a character grid, explicit loading failures and unsupported-character warnings. The page is responsive and honors reduced motion. `site/` is ready for a later static deployment after licensing and publication are approved; no public site is claimed at this stage.

## Verification

```sh
python -m pip install -r requirements-qa.txt
python tools/check_candidates.py
# macOS only; process-scoped registration, not a persistent installation:
swift tools/check_coretext.swift
# Requires Google Chrome and the local specimen server:
python tools/check_site.py
```

Reports stay in ignored `.release-work/`. FontBakery must be run separately for each family and desktop format. The full universal profile is **not all-green**: the project retains a capital Greek sigma in its limited symbol inventory but lacks its lowercase counterpart. This one coverage issue is reported for all 64 desktop files; see the exact counts and remaining warnings in [QA-0.301](docs/QA-0.301.md). No test failure is silently excluded.

## Rights and provenance

Commercial use is the intended release goal, **not a permission granted by this candidate**. No OFL, MIT or other distribution license has been applied yet. See [RIGHTS.zh-CN.md](RIGHTS.zh-CN.md) and [provenance](docs/PROVENANCE.md). The original project and supplied design boards remain intact on the owner's computer. Build dependencies retain their own licenses and are not bundled. No installed or third-party font files are imported or repackaged by the build.
