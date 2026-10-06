# Independent weight masters / 独立字重母版

`masters/LihuiT/{100,300,400,500,600,700,800,900}.json` and the equivalent
`masters/zayJu/` files are the **authoritative font drawing sources**. Every file
contains its own 945 glyph drawings, 810-codepoint mapping, advance widths,
anchors and feature classifications. SVG path commands retain editable cubic
control points and intentional straight edges. One glyph per line keeps diffs
focused. These are static masters, not a variable-font interpolation setup.

A normal `python build.py` reads the requested weight's file only. It does not
read another weight, the reference image, an installed font, or a polygon-offset
recipe. A missing master is an error, not an excuse to generate a synthetic
weight. Each upright master has a documented 10-degree Oblique transform; these
are not 16 additional hand-drawn italics.

## 编辑单个字重

```sh
python tools/master_svg.py export --family LihuiT --weight 100 --glyph e --svg /tmp/LihuiT-100-e.svg
# Edit the path/control points in an SVG-capable drawing tool. Keep design units.
python tools/master_svg.py import --family LihuiT --weight 100 --glyph e --svg /tmp/LihuiT-100-e.svg
python -m unittest discover -s tests -v
python build.py
python tools/check_outlines.py
python tools/check_conversion.py
```

导入只修改所指定母版中的字形，不会同步“变粗／变细”其他字重。SVG 只接受单一路径和
导出时的 y 轴翻转；编辑器添加的其他变换需要先展开。字宽与锚点保存在同一个 JSON
字形记录中，修改它们也必须审查排版结果。重音组合、替代字形和连字是独立记录：修改
基础字母后应明确复核这些相关字形，工具不会悄悄从旧骨架重新生成并覆盖你的编辑。

## 起点与设计边界

本次从项目已有原创字形迁移成逐字重独立源文件，再分别修正字形连接和有限精度问题；
不声称把两套字族的每个字形从零手绘了一遍。保留 zayJu 中粗字重有意采用的折角造型，
不把所有锐角都磨圆。迁移的局部曲线拟合拒绝记录、零宽回折修正保存在
`masters/migration-report.json`。其中的拟合统计是草稿阶段记录；最终母版和导出文件的
实测结果由 QA 报告给出。

`tools/draft_weight_masters.py` and `tools/drawing/legacy/` are historical
migration helpers, **not production build inputs**. The helper requires an
explicit new output directory and refuses to overwrite existing masters. It
needs `requirements-drawing.txt`; normal builds do not need those dependencies.
Never regenerate authoritative masters to erase later per-weight drawing work.
