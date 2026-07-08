# xiaohongshu_note

Android showcase for drafting a Xiaohongshu note through ADB.

这是一个“小红书发笔记”的 Android showcase。它的目标不是提供一套放之四海皆准的坐标，而是展示 Harness/Skill 如何把移动端真实副作用流程做得更稳：

- 操作节奏使用随机慢等待，不做机器式连点。
- 坐标用 0~1 屏幕比例，按设备和 App 版本放在 profile JSON 中。
- 默认停在最终发布前，并截图留证。
- 只有显式传 `--confirm-post` 才会点击最终发布按钮。
- 点击发布后仍返回 `pending_confirmation`，需要人工或 SOP 回看确认。

## Prerequisites / 前置条件

1. Android platform-tools / ADB 可用。
2. 手机已登录小红书，并停留在稳定的首页或可启动小红书。
3. 如果要输入中文/emoji/换行文案，设备需要安装并启用 ADBKeyboard。
4. 先用截图标定当前设备的小红书坐标 profile。

## Profile

先生成示例 profile：

```bash
python run.py showcase/android/xiaohongshu_note/xiaohongshu_note -- --print-example-profile
```

把输出保存成 `data/xhs_profile.json` 后，按你手机上的实际 UI 调整各坐标：

```json
{
  "coords": {
    "create_button": [0.5, 0.94],
    "album_entry": [0.18, 0.83],
    "first_media": [0.14, 0.23],
    "next_button": [0.88, 0.94],
    "caption_input": [0.18, 0.42],
    "publish_button": [0.86, 0.93]
  }
}
```

## Usage / 用法

默认不点最终发布：

```bash
python run.py showcase/android/xiaohongshu_note/xiaohongshu_note -- \
  --profile data/xhs_profile.json \
  --caption "今天的记录\n慢慢来，不要太快" \
  --media data/demo.jpg
```

确认要真实发布时才加：

```bash
python run.py showcase/android/xiaohongshu_note/xiaohongshu_note -- \
  --profile data/xhs_profile.json \
  --caption "今天的记录" \
  --media data/demo.jpg \
  --confirm-post
```

`--confirm-post` 会产生真实外部副作用。发布后脚本只标记为 `pending_confirmation`，不要把点击完成等同于发布成功。
