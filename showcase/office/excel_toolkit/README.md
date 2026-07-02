# excel_toolkit — Excel 读写工具

用 `openpyxl` 直接读写 `.xlsx` 文件结构，不需要打开 Excel 应用，不需要屏幕，服务器上也能跑（cron 定时任务的典型场景）。

## 用法

```bash
# 读取 Excel，输出为 JSON
python run.py showcase/office/excel_toolkit/excel_toolkit -- --read data.xlsx

# 读取指定 sheet
python run.py showcase/office/excel_toolkit/excel_toolkit -- --read data.xlsx --sheet "Sheet2"

# 写入数据到新 Excel
python run.py showcase/office/excel_toolkit/excel_toolkit -- \
  --write output.xlsx --data '[{"姓名":"张三","分数":90},{"姓名":"李四","分数":85}]'
```

## 参数

| 参数 | 说明 |
|---|---|
| `--read` | 读取的 Excel 文件路径，读取结果按 JSON 打印到终端 |
| `--write` | 写入的 Excel 文件路径 |
| `--sheet` | 指定 sheet 名称；读取时不填默认取第一个 sheet，写入时不填默认命名为 `Sheet1` |
| `--data` | 配合 `--write` 使用，JSON 数组，每项是一行的字段字典，第一行的 key 会作为表头 |

## 适用场景

- 定时任务读取业务系统导出的 Excel，转成 JSON 供后续脚本处理
- 把处理结果批量写成 Excel 报表，再走 `connectors/feishu.py` 之类的渠道发出去

## 局限

- 不支持读写图表、公式计算结果以外的复杂样式（`openpyxl` 能读公式文本，`data_only=True` 读的是缓存的计算结果，不重新计算）
- 大文件（几十万行以上）建议用 `openpyxl` 的 `read_only`/`write_only` 模式，本示例为简化没有用
