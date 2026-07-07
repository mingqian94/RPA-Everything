# adb_basics

Minimal Android automation showcase for `core.android`.

这是 `core.android` 的最小 Android 自动化示例，用来验证 ADB 设备发现、截图、点击、滑动、按键和文件推送等框架能力。

It demonstrates:

- listing ADB devices
- taking a phone screenshot
- tapping by screen ratio
- swiping by screen ratio
- sending key events
- pushing a file to the phone
- running basic diagnostics

示例覆盖：

- 列出 ADB 设备
- 截取手机屏幕
- 按屏幕比例点击
- 按屏幕比例滑动
- 发送 Android 按键事件
- 向手机推送文件
- 运行基础诊断

## Examples / 示例

```bash
python run.py showcase/android/adb_basics/adb_basics -- --devices
python run.py showcase/android/adb_basics/adb_basics -- --diagnostics
python run.py showcase/android/adb_basics/adb_basics -- --screenshot data/android_screen.png
python run.py showcase/android/adb_basics/adb_basics -- --tap-ratio 0.5 0.5
python run.py showcase/android/adb_basics/adb_basics -- --swipe-ratio 0.5 0.8 0.5 0.2
python run.py showcase/android/adb_basics/adb_basics -- --key KEYCODE_BACK
python run.py showcase/android/adb_basics/adb_basics -- --push local.png /sdcard/Pictures/local.png --media-scan
```

`--diagnostics-input` is opt-in because it sends `KEYCODE_HOME` to the phone.

`--diagnostics-input` 默认不执行，因为它会向手机发送 `KEYCODE_HOME`。
