# extract_table — 网页表格提取

从任意需要登录的 Web 系统中提取表格数据，保存为 CSV 或直接输出 JSON。

## 前置条件

Chrome 以调试端口启动，并已在浏览器中登录目标系统：

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Windows
chrome.exe --remote-debugging-port=9222
```

## 用法

```bash
# 提取当前浏览器页面的第一张表格，打印到终端
/opt/homebrew/bin/python3.12 run.py showcase/web/extract_table/extract_table

# 打开指定 URL 后提取
/opt/homebrew/bin/python3.12 run.py showcase/web/extract_table/extract_table -- \
  --url "https://your-system.com/data/list"

# 先在搜索框输入关键词过滤，再提取
/opt/homebrew/bin/python3.12 run.py showcase/web/extract_table/extract_table -- \
  --url "https://your-system.com/data/list" \
  --filter "2024-06" \
  --output result.csv

# 页面有多张表格时，指定第二张（从 0 开始）
/opt/homebrew/bin/python3.12 run.py showcase/web/extract_table/extract_table -- \
  --table-index 1
```

## 参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--url` | 当前页面 | 目标页面地址 |
| `--filter` | 无 | 搜索框关键词 |
| `--search-selector` | 自动猜测 | 搜索框 CSS 选择器 |
| `--table-index` | 0 | 提取第几张表格 |
| `--output` | 无（打印） | 保存为 CSV 的路径 |

## 输出格式

不指定 `--output` 时，打印 JSON：

```json
[
  {"姓名": "张三", "部门": "产品", "状态": "在职"},
  {"姓名": "李四", "部门": "研发", "状态": "在职"}
]
```

## 限制

- 只支持标准 HTML `<table>` 标签，React/Vue 虚拟列表（非 table 渲染）无法提取
- 分页数据只提取当前页；多页提取需在此基础上扩展翻页逻辑
- 动态加载（滚动加载）的表格需等待数据渲染完成后再运行
