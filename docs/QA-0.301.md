# 0.301 本地候选：实际验证与发行边界

状态：已重建、已运行本地网页与原生字体检查；**尚未正式发布、尚未应用对外许可**。本报告不是侵权风险保证，也不是人工设计签字。

## 输入与名称

本轮从作者提供的 0.300 源工程导出独立工作副本，原工程与设计稿未修改。Lihui 改为 **LihuiT**，Zixian 改为 **zayJu**；作者仍为 **zayju**。最终候选共 32 款样式、96 个格式文件；每款 945 个 glyph、810 个 Unicode 编码字符。源码输入与候选逐文件 SHA-256 在 [机器可读记录](qa/candidate-0.301.json) 中。

## 已实际通过的检查

| 检查 | 本轮结果 | 不代表什么 |
| --- | --- | --- |
| 构建程序结构检查 | 96 / 96 文件通过 | 不替代独立工具或视觉审查 |
| OpenType Sanitizer 9.2.0 | 96 / 96 文件退出码 0；检查期间原文件 SHA-256 不变 | 不是许可证审查，不证明所有应用都兼容 |
| HarfBuzz（uharfbuzz 0.56.2） | 96 个候选 × 15 项断言 = **1,440 项通过** | 是固定特性样本，不等于所有语言组合全部审校 |
| macOS CoreText | 64 个 TTF / OTF，448 行样文；确认 PostScript 名、实际文件 URL、无回退 | **仅进程内注册**，不是字体册／用户字体目录安装或设计软件人工验收 |
| Chrome 154.0.8037.93 | 32 个真实 WOFF2 均返回 HTTP 200 并完成 FontFace 加载 | 不等于 Safari、Firefox、Windows 或移动真机全部验证 |
| 页面与交互 | 1440 / 900 / 390 像素宽度无横向溢出；字族／字重／Oblique／ss05、重置、深色、字符表、缺字提示、字体请求失败、减少动画偏好通过 | 390 像素视口是桌面浏览器模拟，不是手机真机测试 |

环境：macOS 26.6.2（25G83）；独立 Python 3.13.2 环境。构建依赖 FontTools 4.63.0、Shapely 2.1.2、Brotli 1.2.0。没有导入、复制或改名任何系统字体。CoreText 绘制了 Regular / Bold 的本机排印 PNG，网页截图也来自真正加载字体后的页面。

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

## 尚未完成的发行门槛

对外许可证与适用范围仍待权利方确认，name ID 14 尚未写入已生效的发行许可网址。没有发布下载附件，没有宣称免费商用已经获准。

固定样文和页面已做程序检查及截图查看；完整字符与八个字重的人工光学校正、目标设计软件实际安装／导出验收、其他操作系统和浏览器验收未完成。完整 FontBakery 的覆盖问题与告警按上文公开保留。正式发布前需确定处理方案和接受范围，不能仅凭本轮多数检查通过就宣称“全平台正式商用验收完成”。

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
