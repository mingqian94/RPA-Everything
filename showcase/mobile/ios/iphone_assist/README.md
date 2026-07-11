# iPhone Semi-Automation Assistant

Reusable iPhone helper for workflows where a Harness Agent can prepare the phone
but a human must finish the final UI steps.

```bash
python run.py showcase/mobile/ios/iphone_assist/iphone_assist -- --devices
python run.py showcase/mobile/ios/iphone_assist/iphone_assist -- --diagnostics
python run.py showcase/mobile/ios/iphone_assist/iphone_assist -- --copy-text "Draft text" --launch-wechat
```

Current boundary:

- USB device discovery through `pymobiledevice3`
- best-effort WiFi discovery for online identity checks
- Developer Mode / DeveloperDiskImage readiness check
- copy text to the iPhone clipboard
- launch an app by bundle id, for example `com.tencent.xin`
- screenshot for evidence

This is not full iPhone remote control. On the iOS 26.x devices borrowed from
`wechat-moment`, CoreDevice remote touch required iOS 27.0+, and WDA/XCUITest
needed a separately signed runner. Final selection, posting, sending, or approval
steps should be treated as manual confirmation unless a future signed runner is
added and verified.
