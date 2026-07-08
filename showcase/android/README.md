# Android Showcase

Android skills drive a real Android phone from the PC through ADB. This is a
separate automation route from browser and desktop automation:

- Browser: operate Chrome pages through Playwright/CDP.
- Desktop: operate the local Windows/macOS screen.
- Android: operate a connected phone through `adb`.

Android Skill 通过 ADB 让电脑操作真实 Android 手机，是独立于浏览器自动化和桌面自动化的第三类 UI 自动化路线：

- 浏览器：通过 Playwright/CDP 操作 Chrome 页面。
- 桌面：操作本机 Windows/macOS 屏幕。
- Android：通过 `adb` 操作已连接手机。

## Prerequisites / 前置条件

1. Install Android platform-tools and make `adb` available on `PATH`, or set:

   安装 Android platform-tools，并确保 `adb` 在 `PATH` 中；也可以在配置中显式指定：

```yaml
android:
  adb_path: D:\path\to\platform-tools\adb.exe
```

2. Enable USB debugging on the phone.

   在手机上开启 USB 调试。

3. For synthetic taps on MIUI/HyperOS, enable USB debugging (Security settings),
   reboot the phone, and reconnect ADB.

   MIUI/HyperOS 上如果需要模拟点击，通常还要开启“USB 调试（安全设置）”，然后重启手机并重新连接 ADB。

## Showcase / 示例

```bash
python run.py showcase/android/adb_basics/adb_basics -- --devices
python run.py showcase/android/adb_basics/adb_basics -- --diagnostics
python run.py showcase/android/adb_basics/adb_basics -- --screenshot data/android_screen.png
python run.py showcase/android/adb_basics/adb_basics -- --tap-ratio 0.5 0.5
python run.py showcase/android/adb_basics/adb_basics -- --key KEYCODE_HOME
```

Use `--serial <device>` when multiple devices are connected.

连接多台设备时，用 `--serial <device>` 指定目标设备。

## Xiaohongshu Note / 小红书笔记

This showcase demonstrates a slower, safer mobile-app flow. It drafts a
Xiaohongshu note through ADB and stops before the final publish button unless
`--confirm-post` is explicitly provided.

这个示例演示更谨慎的移动端 App 流程：通过 ADB 起草小红书笔记，默认停在最终发布前；只有显式传入
`--confirm-post` 才会点击发布。

```bash
python run.py showcase/android/xiaohongshu_note/xiaohongshu_note -- --print-example-profile
python run.py showcase/android/xiaohongshu_note/xiaohongshu_note -- --profile data/xhs_profile.json --dry-run
```
