# LihuiT & zayJu

**一套为文字，一套为表达。** zayju 的配套几何无衬线字体。

[English](README.md) · [首发进度](https://github.com/SheathedSharp/oh-my-font/issues/1) · [本轮实际检查](docs/QA-0.301.md)

![使用实际 WOFF2 字体渲染的本地展示页](docs/images/specimen-preview.png)

**当前是 0.301 本地发行候选，不是已经获得商用许可的正式下载包。** 最终对外许可与设计／应用验收尚未完成。图中网页已在作者 Mac 上运行，不代表已经部署了公开网站。

## 两套字族

| 新名称 | 用途与特点 | 原工程名称 |
| --- | --- | --- |
| **LihuiT** | 正文／界面，较宽松的字距，默认 I / l 更易辨认 | Lihui |
| **zayJu** | 标题，宽阔比例、开放 a / g、分离收笔的 y | Zixian |

字体菜单、PostScript 名称、文件名及构建选择器均使用新名称；作者署名仍为小写 **zayju**。两套字族各有 8 个静态字重和正体／10° Oblique，共 32 款样式。每款输出 TTF、CFF OTF、WOFF2，共 96 个本地文件。每款包含 945 个 glyph、810 个 Unicode 编码字符。

**没有汉字，不是等宽编程字体，也不是可变字体。** 字重是 100、300、400、500、600、700、800、900，没有 200 档。Oblique 是倾斜款，不冒充独立设计的 Italic。zayJu 的 I / l 强区分可启用 `ss05`。

## 本地构建与试用

需要 Python 3.10 或更新版本。依赖安装到工程自己的 `.venv`；不修改系统字体目录。

```sh
python3 build-local.py
.venv/bin/python tools/prepare_site.py
.venv/bin/python -m http.server 8136 --bind 127.0.0.1 --directory site
```

Windows 使用 `.venv\Scripts\python.exe` 替代 `.venv/bin/python`。也可以使用保留的 `build-macos.command`、`build-linux.sh`、`build-windows.cmd` 构建入口。三平台入口的保留不等于本轮在三平台都运行过。

在运行服务器的电脑打开 `http://127.0.0.1:8136/`。展示页有可编辑文字、两字族与全部字重／Oblique、字号、字距、OpenType 开关、浅／深色模式、完整字符表。网页加载真实 WOFF2；字体失败会明确报错，不用系统字体冒充。输入不受支持的字符时会提示回退。

生成目录为 `dist/{ttf,otf,woff2}/{LihuiT,zayJu}/`。TTF 和 OTF 是相同设计的两种桌面格式，将来安装时二选一，避免重复身份。WOFF2 用于网页，不是桌面安装格式。

## 这轮确实检查了什么

96 个文件通过构建程序的结构检查和 OTS 检查；HarfBuzz 对每个格式的每款字体运行了 15 项排版断言。macOS CoreText 对 64 个桌面文件完成进程内注册，并核对实际加载路径与固定样文不存在字体回退。Chrome 对真实 WOFF2、交互和三种页面宽度完成检查。

FontBakery 按字族与格式分成四组运行，**完整 universal profile 尚非全绿**：现有符号范围含大写希腊 Σ，但不含小写 σ；同一覆盖问题在 64 个桌面文件上重复报告。其余告警、准确次数、工具版本和未验证边界见 [QA-0.301](docs/QA-0.301.md)。没有将进程内注册包装成字体册安装验收，也没有声称 Windows／手机系统字体替换已验证。

## 许可与来源

商用是发行目标，**当前候选尚未授予商用、改版或再分发许可**。本轮没有应用 OFL、MIT 或其他对外许可证。请阅读 [RIGHTS.zh-CN.md](RIGHTS.zh-CN.md) 与 [来源记录](docs/PROVENANCE.md)。原工程、旧成品、原设计稿保留在作者本机，没有被覆盖或删除。构建程序不读取、不改名、不打包系统字体；第三方构建依赖单独安装，保留各自许可。
