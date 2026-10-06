# LihuiT & zayJu

**一套为文字，一套为表达。** zayju 的配套几何无衬线字体。

[English](README.md) · [在线试用](https://fonts.zayju.de/) · [下载 v0.301](https://github.com/SheathedSharp/oh-my-font/releases/tag/v0.301) · [来源与署名](ATTRIBUTION.txt)

![真实 WOFF2 字体渲染的展示网页](docs/images/specimen-preview.png)

## 免费商用，保留来源

**采用 SIL Open Font License 1.1，不设置保留字体名称。** 作者为 **zayju**，原始来源为 [SheathedSharp/oh-my-font](https://github.com/SheathedSharp/oh-my-font)。字体元数据、每个发行包和展示页都保留作者与来源。

再分发字体原版或修改版时，须按 OFL 保留版权声明与许可证；版权声明已包含原始仓库地址。建议同时保留 `ATTRIBUTION.txt`。普通海报、网页内容或其他商用作品仅使用字体排版，不额外强制在作品上署名。没有修改 OFL 原条款，也没有额外增加“作品必须鸣谢”的限制。详见 [OFL.txt](OFL.txt)、[许可范围](LICENSE.md) 与 [署名说明](ATTRIBUTION.txt)。

## 下载哪个包

**桌面安装选 TTF 或 OTF 之一，不要同时安装两种**，因为它们使用同一套字体身份。WOFF2 用于网页；Website 包是可直接部署的完整交互展示页。各包都带许可证、来源说明和包内校验值；Release 的 `SHA256SUMS.txt`、`BUILD-MANIFEST.json` 与 `QA.json` 对应最终下载文件和源码。不要把 GitHub 自动提供的 Source code 当成字体安装包。

| 字族 | 定位 | 原工程名称 |
| --- | --- | --- |
| **LihuiT** | 正文／界面，较宽松字距，默认 I / l 更易辨认 | Lihui |
| **zayJu** | 标题，宽阔比例、开放 a / g、分离收笔的 y | Zixian |

每套字族有 8 个静态字重和正体／10° Oblique，总计 **32 款样式、96 个格式文件**。字重为 100、300、400、500、600、700、800、900；每款包含 **945 个字形、810 个 Unicode 编码字符**。作者署名仍为小写 **zayju**。

这是首个公开 **0.301** 发行，**不代表全语言、全平台或逐字光学校正已经完成**。不含汉字、完整希腊文／西里尔文、可变轴或等宽编程字族；Oblique 不是独立设计的 Italic。zayJu 的 I / l 强区分可启用 `ss05`。剩余 FontBakery 问题及验证范围在 [QA 报告](docs/QA-0.301.md) 中公开记录，后续完善由 [Issue #3](https://github.com/SheathedSharp/oh-my-font/issues/3) 跟踪。

## 本地构建与网页

需要 Python 3.10+。构建使用工程自己的 `.venv`，不会自动安装字体。

```sh
python3 build-local.py
.venv/bin/python tools/prepare_site.py
.venv/bin/python -m http.server 8136 --bind 127.0.0.1 --directory site
```

Windows 将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。构建入口保留不等于本轮已完成 Windows 真机验收。

本机打开 `http://127.0.0.1:8136/`；网页加载真实 WOFF2，支持文字编辑、字族、全部字重与 Oblique、字号字距、OpenType 特性、字符表和深色模式；缺字／加载失败会提示，页面适配不同宽度并尊重减少动画偏好。

## 验证、发布与来源

最终字体完成 OTS、固定 HarfBuzz 排版、真实浏览器加载检查。macOS 还完成进程内 CoreText 检查，以及 32 款 TTF 的用户目录安装、独立 AppKit 字体查找、粗体／Oblique 样式关联及 RTF 导入导出。**完整 FontBakery universal profile 仍保留有明确范围解释的 Σ/σ 覆盖失败与告警；没有把它们隐藏成全绿。**

复现步骤、发行与部署见 [RELEASING](docs/RELEASING.md)。原工程、原成品与原设计稿没有覆盖或删除；来源范围见 [PROVENANCE](docs/PROVENANCE.md)。第三方依赖不随字体包分发，保留各自许可。OFL 授权不等同于全球独占权或零侵权风险保证。
