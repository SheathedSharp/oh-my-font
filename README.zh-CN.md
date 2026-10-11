# LihuiT & zayJu

**一套为文字，一套为表达。** zayju 的配套人文与展示无衬线字体。

[English](README.md) · [在线试用](https://fonts.zayju.de/) · [v0.500 候选](https://github.com/SheathedSharp/oh-my-font/releases/tag/v0.500) · [已发布的 v0.400](https://github.com/SheathedSharp/oh-my-font/releases/tag/v0.400) · [来源与署名](ATTRIBUTION.txt)

![真实 WOFF2 字体渲染的展示网页](docs/images/specimen-preview.png)

## 免费商用，保留来源

**采用 SIL Open Font License 1.1，不设置保留字体名称。** 作者为 **zayju**，原始来源为 [SheathedSharp/oh-my-font](https://github.com/SheathedSharp/oh-my-font)。字体元数据、每个发行包和展示页都保留作者与来源。

再分发字体原版或修改版时，须按 OFL 保留版权声明与许可证；版权声明已包含原始仓库地址。建议同时保留 `ATTRIBUTION.txt`。普通海报、网页内容或其他商用作品仅使用字体排版，不额外强制在作品上署名。没有修改 OFL 原条款，也没有额外增加“作品必须鸣谢”的限制。详见 [OFL.txt](OFL.txt)、[许可范围](LICENSE.md) 与 [署名说明](ATTRIBUTION.txt)。

## 下载哪个包

**桌面安装选 TTF 或 OTF 之一，不要同时安装两种**，因为它们使用同一套字体身份。WOFF2 用于网页；Website 包是可直接部署的完整交互展示页。各包都带许可证、来源说明和包内校验值；Release 的 `SHA256SUMS.txt`、`BUILD-MANIFEST.json` 与 `QA.json` 对应最终下载文件和源码。不要把 GitHub 自动提供的 Source code 当成字体安装包。

| 字族 | 定位 | 原工程名称 |
| --- | --- | --- |
| **LihuiT** | 正文／界面，较宽松字距，默认 I / l 更易辨认 | Lihui |
| **zayJu** | 展示／品牌表达，流动曲线、鲜明 B / M / R 与双层 g | Zixian |

**0.500 是基于该重绘的第一套多字重家族。** 每个字族包含正体 100、300、400、500、600、700、800、900，以及每个字重的 10° Oblique，共 32 款样式，各有 TTF、CFF OTF、WOFF2。每款仍是 **986 个字形、810 个编码字符** 和同一组 21 个 OpenType 功能。Regular 400 正体就是已验收的 0.400 稿。其余正体是单独存放的 master，理由见 [字重说明](docs/design/0.500-weights.md)。Oblique 标注为 Oblique，不是单独绘制的 Italic。

[旧 0.301](https://github.com/SheathedSharp/oh-my-font/releases/tag/v0.301) 只作为历史版本保留。不要把它和 0.500 混成一套。安装前请停用旧字体；TTF 与 OTF 只选一种。在人工目检完成并打上 v0.500 标签之前，已发布的最新版本仍是 v0.400。

不含汉字、完整希腊文／西里尔文、可变轴或等宽编程字族。[0.500 验证](docs/QA-0.500.md) 保留既有的 Sigma 覆盖 FAIL，并记录全部警告。更广覆盖仍由 [Issue #3](https://github.com/SheathedSharp/oh-my-font/issues/3) 跟踪。

## 本地构建与网页

需要 Python 3.10+。构建使用工程自己的 `.venv`，不会自动安装字体。

```sh
python3 build-local.py
.venv/bin/python tools/prepare_site.py
.venv/bin/python -m http.server 8136 --bind 127.0.0.1 --directory site
```

Windows 将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。构建入口保留不等于本轮已完成 Windows 真机验收。

本机打开 `http://127.0.0.1:8136/`；网页加载真实 WOFF2，支持文字编辑、字族、本次发布的 Regular 400 正体、字号字距、OpenType 特性、字符表和深色模式；缺字／加载失败会提示，页面适配不同宽度并尊重减少动画偏好。

## 验证、发布与来源

最终文件会检查每个字形是否与已验收源稿完全一致，包含结构、OTS、默认及替代字形的重音排版、跨格式和独立目录重复构建。浏览器加载并校验真实 WOFF2；macOS 检查准确文件与实际排版，不持久安装字体。**FontBakery 完整 universal profile 仍保留精确匹配的 Σ/σ 覆盖失败与告警，不冒充全绿。**

复现步骤、发行与部署见 [RELEASING](docs/RELEASING.md)。原工程、原成品与原设计稿没有覆盖或删除；来源范围见 [PROVENANCE](docs/PROVENANCE.md)。第三方依赖不随字体包分发，保留各自许可。OFL 授权不等同于全球独占权或零侵权风险保证。

当前绘图主源在 `design/full-01/sources/*.ufo`，一字形一 GLIF；Glyphs 副本经过往返验证。`src/` 下的历史几何脚本已不参与正式构建，旧版可从对应 tag 重建。
