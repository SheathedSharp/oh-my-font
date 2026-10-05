# 0.301 发行：实际验证、来源与范围

**许可证：SIL OFL 1.1，不设保留字体名称。** 作者与原始仓库网址写入版权声明、完整字体许可元数据和每个发行包。以下检查对应最终获许可的 0.301 字体文件，不借用旧未授权候选的哈希。本报告不是侵权风险保证，也不是作者逐字设计签字。

## 输入与名称

本轮从作者提供的 0.300 源工程导出独立工作副本，原工程与设计稿未修改。Lihui 改为 **LihuiT**，Zixian 改为 **zayJu**；作者仍为 **zayju**。最终候选共 32 款样式、96 个格式文件；每款 945 个 glyph、810 个 Unicode 编码字符。源码输入与候选逐文件 SHA-256 在 [机器可读记录](qa/release-0.301.json) 中。

## 已实际通过的检查

| 检查 | 本轮结果 | 不代表什么 |
| --- | --- | --- |
| 构建程序结构检查 | 96 / 96 文件通过 | 不替代独立工具或视觉审查 |
| OpenType Sanitizer 9.2.0 | 96 / 96 文件退出码 0；检查期间原文件 SHA-256 不变 | 不是许可证审查，不证明所有应用都兼容 |
| HarfBuzz（uharfbuzz 0.56.2） | 96 个候选 × 15 项断言 = **1,440 项通过** | 是固定特性样本，不等于所有语言组合全部审校 |
| macOS CoreText | 64 个 TTF / OTF，448 行样文；确认 PostScript 名、实际文件 URL、无回退 | **仅进程内注册**，不是字体册／用户字体目录安装或设计软件人工验收 |
| Chrome 154.0.8037.93 | 32 个真实 WOFF2 均返回 HTTP 200 并完成 FontFace 加载 | 不等于 Safari、Firefox、Windows 或移动真机全部验证 |
| 页面与交互 | 1440 / 900 / 390 像素宽度无横向溢出；字族／字重／Oblique／ss05、重置、深色、字符表、缺字提示、字体请求失败、减少动画偏好通过 | 390 像素视口是桌面浏览器模拟，不是手机真机测试 |

环境：macOS 26.6.2（25G83）；独立 Python 3.13.2 环境。构建依赖 FontTools 4.63.0、Shapely 2.1.2、Brotli 1.2.0。没有导入、复制或改名任何第三方系统字体；用户目录安装只涉及本项目自己生成的 TTF。CoreText 绘制了 Regular / Bold 的本机排印 PNG，网页截图也来自真正加载字体后的页面。

固定排版断言覆盖标准／可选连字、ss01–ss05、斜线零与等宽数字、分数、上下标、AV 字距，以及叠加重音。完整测试实现保留在 `tools/`，非空图片检查不能替代这些断言，也不能替代人工视觉验收。

## FontBakery：没有隐瞒失败

FontBakery **1.1.0** 的 `check-universal --skip-network` 按“字族 × 桌面格式”分别运行。网络检查未运行；跳过次数按工具原报告保留。

| 检查组 | PASS | FAIL | WARN | INFO | SKIP |
| --- | ---: | ---: | ---: | ---: | ---: |
| LihuiT / TTF | 1100 | 16 | 80 | 48 | 608 |
| zayJu / TTF | 1100 | 16 | 80 | 48 | 608 |
| LihuiT / OTF | 1004 | 16 | 48 | 48 | 736 |
| zayJu / OTF | 1004 | 16 | 48 | 48 | 736 |

剩余 FAIL 均为同一类 `case_mapping`：字体的有限符号集合含 **U+03A3 Σ**，但缺少对应 **U+03C3 σ**。这是一个覆盖范围问题在 64 个文件中的重复，不是 64 个互不相关的缺陷。当前不宣称完整希腊文支持，也没有为了得到绿色结果随意新增一个未设计的字形或移除现有字符。**未使用排除参数隐藏该失败，完整 universal profile 仍返回非零。**

剩余 WARN 涉及：分解轮廓的 caron 自动检查限制、部分非典型轮廓数量、连字缺少 GDEF 插入光标位置、数学符号宽度不一致、存在软连字符。这些分别需要设计审阅或明确的范围处理，不能统一写成“都不影响使用”。

最初曾把两字族及 TTF / OTF 混在一次命令中，造成家族分组与重复身份误报。该探索性结果没有当作最终质量统计；以上四组是修正调用方式后的独立结果。

## 已修正的构建问题

- 从实际 cmap 重算 OS/2 码页字段，修正原始全零情况。
- 修正非 Bold 正体的 Regular 样式标志，统一同族下划线厚度。
- 保留现代 Unicode / Windows 名称记录，移除冗余 Mac Roman 名称；中文环境的字族元数据也使用 LihuiT / zayJu。
- 给静态正体的 STAT ital 值补关联值；无手工 hinting 的 TTF 增加标准 scan-control `prep`。**这不是逐字自动或人工 hinting。**

## 接受范围与后续完善

本轮已经应用正式 OFL，并检查每款字体的 name ID 0/9/11/13/14：版权声明含原始来源、作者为 zayju、项目网址准确、ID 13 含完整 OFL、ID 14 指向官方许可站点。每个包携带 OFL.txt、ATTRIBUTION.txt、AUTHORS.txt、FONTLOG.txt 与源码提交信息。普通商用作品不增加强制可见署名要求。

另外完成 **32 款 TTF 的实际用户目录安装**，随后从独立 AppKit 进程检查真实文件路径、两字族原生粗体／Oblique 关联、32 款字体的 RTF 导出／重新导入。安装后的固定样文 RTF 已用 TextEdit 打开。字体位于新建的版本专用用户目录，没有覆盖旧字体；这与前述进程内 CoreText 注册是两种分别记录的检查。第一次刚复制完成时字体数据库尚未更新，初次 AppKit 查找未通过；字体索引更新后独立进程重跑通过，没有把初次失败涂绿。

首次发行接受的是范围明确的拉丁正文／标题字族，不是完整希腊文、数学或编程字族。保留已存在的 Σ，避免为通过测试临时发明未审阅的 σ 或删改字符。`tools/check_fontbakery.py` **仍运行完整 universal profile 并保留原始退出码 1**，仅对唯一、精确匹配的 Σ/σ 失败作有记录的发行范围例外；出现其他 FAIL/ERROR 会阻止发行。其余告警不统一宣称无影响，而是按上文列出的文本编辑、数学排版、字符审校边界披露。

固定样文和实际页面已经查看；完整字符、全部字重的逐字光学校正、更多设计软件、其他系统／浏览器以及语言学验收仍属后续工作，跟踪于 [Issue #3](https://github.com/SheathedSharp/oh-my-font/issues/3)。**首发交付完成不等于这些后续工作已完成，也不等于完整 FontBakery 全绿或 Google Fonts 收录验收。**

## 复现入口

```sh
python -m pip install -r requirements.txt -r requirements-qa.txt
python build.py
python tools/check_candidates.py
swift tools/check_coretext.swift  # macOS only
python tools/prepare_site.py
python -m http.server 8136 --bind 127.0.0.1 --directory site
# 在另一个终端：
python tools/check_site.py
```

FontBakery 对每组单独执行，例如：

```sh
fontbakery check-universal --skip-network --no-progress --no-colors \
  --json .release-work/fontbakery-ttf-LihuiT.json 'dist/ttf/LihuiT/*.ttf'
```

原始详细日志留在本机忽略目录 `.release-work/`，避免把本机绝对路径和大批重复诊断写入公开仓库。公开记录含摘要、相对文件名和哈希，不能冒充全部原始日志。
