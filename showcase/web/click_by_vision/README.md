# click_by_vision — 视觉识别点击

截图当前页面，用 LLM Vision 找到目标元素并点击。适用于选择器不稳定或 DOM 被混淆的页面。

## 前提条件

- Chrome 以调试端口启动：`sh tools/start_chrome.sh`
- config.yaml 中 `model` 设为多模态模型（`claude-sonnet-4-6` 或内网网关等价模型）

## 参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `--action` | ✅ | 要点击的元素描述，越具体越准确 |
| `--url` | 否 | 目标页面 URL；留空则使用当前浏览器页面 |
| `--dry-run` | 否 | 只截图识别坐标，不实际点击，用于验证 |

## 运行示例

```bash
# 点击指定页面的导出按钮
python run.py showcase/web/click_by_vision -- \
  --url "https://example.com/admin" \
  --action "右上角的「导出数据」按钮"

# 在当前浏览器页面点击
python run.py showcase/web/click_by_vision -- \
  --action "表格第一行的「编辑」链接"

# 只识别不点击（调试用）
python run.py showcase/web/click_by_vision -- \
  --url "https://example.com" --action "导出按钮" --dry-run
```

## 注意

- `--action` 描述越具体，识别成功率越高；避免使用"按钮"等过于通用的描述
- 识别失败时会打印提示，不会抛异常；可用 `--dry-run` 先确认 LLM 能找到目标
- 每次调用需一次 LLM 视觉推理，有 token 成本；高频场景建议改用固定 CSS 选择器
