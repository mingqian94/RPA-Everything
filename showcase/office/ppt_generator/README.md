# ppt_generator — 从结构化内容生成 PPT

用 `python-pptx` 直接生成 `.pptx` 文件，不需要打开 PowerPoint / Keynote，不需要屏幕。
适合周报、月报这类排版固定、内容每次变化的汇报 PPT。

## 用法

```bash
python run.py showcase/office/ppt_generator/ppt_generator -- \
  --output weekly_report.pptx \
  --data '[
    {"title": "本周进展", "bullets": ["完成 A", "完成 B"]},
    {"title": "下周计划", "bullets": ["开始 C"]}
  ]'
```

## 参数

| 参数 | 说明 |
|---|---|
| `--data` | JSON 数组，每项是一页幻灯片，格式 `{"title": "标题", "bullets": ["要点1", "要点2"]}` |
| `--output` | 输出的 `.pptx` 路径 |

## 适用场景

- 数据周报/月报：把统计脚本的输出直接组装成幻灯片内容，跳过手动复制粘贴
- 需要固定模板反复生成的汇报材料

## 局限

- 当前示例只用了默认的"标题+内容"版式（`slide_layouts[1]`），不支持图表、图片、自定义主题
- 如果需要贴公司统一模板（logo、配色），可以用 `Presentation("模板文件.pptx")` 打开现成模板再往里加页，而不是 `Presentation()` 建空白文档——`python-pptx` 支持基于已有 `.pptx` 模板继续编辑
