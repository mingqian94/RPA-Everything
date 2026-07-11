# Android Smoke Test

Non-destructive real-device checks for the Android automation stack.

```bash
python run.py showcase/android/smoke_test/smoke_test -- --output data/outputs/android_smoke.json
```

Checks:

- ADB device discovery
- device online state
- hardware serial identity
- resolution
- screenshot
- UIAutomator dump
- ADBKeyboard package presence

Input injection is off by default. Use `--include-input-check` only when it is acceptable to send `KEYCODE_HOME`.

File transfer is also off by default. Use `--include-file-check` to create and delete a tiny probe file under `/sdcard/Download`.
