# Demo: Android Draft Preparation

## Goal

Show a real Android device being prepared for a Xiaohongshu draft at a human-like pace. The demo stops before final publishing.

## Prepare

1. Connect a test Android phone with USB debugging enabled.
2. Run `python run.py showcase/android/adb_basics/adb_basics -- --diagnostics`.
3. Prepare a non-sensitive `data/xhs_profile.json` and test media.

## Record

```bash
python run.py showcase/android/xiaohongshu_note/xiaohongshu_note -- --profile data/xhs_profile.json --dry-run
```

For a supervised live draft, omit `--dry-run` but do not pass `--confirm-post`.

## Evidence

- Device diagnostics result
- Before-publish screenshot
- `pending_confirmation` run status

Never use a real customer account, unpublished campaign asset, or final publish action in a public recording.
