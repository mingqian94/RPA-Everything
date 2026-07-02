# word_report — 从结构化内容生成 Word 文档

用 `python-docx` 直接生成 `.docx` 文件，不需要打开 Word，不需要屏幕。
适合通知、简报这类标题+分段正文、格式固定的文档。

## 用法

```bash
python run.py showcase/office/word_report/word_report -- \
  --output report.docx \
  --title "本周数据简报" \
  --data '["第一段内容……", "第二段内容……"]'
```

## 参数

| 参数 | 说明 |
|---|---|
| `--title` | 文档标题（一级标题） |
| `--data` | JSON 数组，字符串列表，每项是一个正文段落 |
| `--output` | 输出的 `.docx` 路径 |

## 适用场景

- 自动生成日报/周报正文，再通过邮件或飞书发出去
- 格式固定的通知类文档批量生成

## 局限

- 当前示例只支持纯文本段落和一级标题，不支持表格、图片、多级标题
- 如果需要贴公司统一模板，同 `ppt_generator`：用 `Document("模板文件.docx")` 打开现成模板再往里加内容，而不是 `Document()` 建空白文档
