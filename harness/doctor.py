"""Environment doctor for first-time RPA-Everything users."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parent.parent


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""
    required: bool = True


def _argv() -> list[str]:
    try:
        sep = sys.argv.index("--")
        return sys.argv[sep + 1:]
    except ValueError:
        return sys.argv[1:]


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def check_python() -> Check:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ok = sys.version_info >= (3, 11)
    return Check(
        "python",
        ok,
        version,
        "Install Python 3.11+ and rerun tools/setup.ps1 or tools/setup.sh.",
    )


def check_python_packages() -> Check:
    modules = {
        "playwright": "playwright",
        "anthropic": "anthropic",
        "mcp": "mcp",
        "yaml": "pyyaml",
        "requests": "requests",
    }
    missing = [label for module, label in modules.items() if not _has_module(module)]
    return Check(
        "python_packages",
        not missing,
        "ok" if not missing else "missing: " + ", ".join(missing),
        "Run: pip install -r requirements.txt",
    )


def check_config() -> Check:
    config = ROOT / "config.yaml"
    if not config.exists():
        return Check(
            "config_yaml",
            False,
            "config.yaml not found",
            "Copy config.yaml.example to config.yaml and fill llm.api_key / llm.model.",
        )
    text = config.read_text(encoding="utf-8", errors="replace")
    placeholder = "<your-anthropic-api-key>" in text
    has_key_hint = "api_key:" in text
    ok = has_key_hint and not placeholder
    return Check(
        "config_yaml",
        ok,
        "exists" if ok else "exists but still looks like a template",
        "Open config.yaml and replace <your-anthropic-api-key> with a real key or gateway key.",
    )


def check_chrome(cdp_url: str = "http://127.0.0.1:9222/json/version") -> Check:
    try:
        with urllib.request.urlopen(cdp_url, timeout=2) as resp:
            body = resp.read().decode("utf-8", "replace")
        ok = '"Browser"' in body or "Chrome" in body
        return Check(
            "chrome_cdp",
            ok,
            "ready at 127.0.0.1:9222" if ok else "port responded but did not look like Chrome DevTools",
            "Run tools\\start_chrome.bat on Windows or sh tools/start_chrome.sh on macOS.",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return Check(
            "chrome_cdp",
            False,
            str(e),
            "Run tools\\start_chrome.bat on Windows or sh tools/start_chrome.sh on macOS.",
            required=False,
        )


def check_android() -> Check:
    try:
        from core.android import list_devices

        devices = list_devices(include_offline=True)
        online = [d for d in devices if d.state == "device"]
        if online:
            return Check("android_adb", True, f"{len(online)} online device(s)", required=False)
        if devices:
            return Check("android_adb", False, "adb sees devices but none are online", "Authorize USB debugging.", False)
        return Check("android_adb", False, "no adb devices", "Connect a phone or skip Android tasks.", False)
    except Exception as e:
        return Check("android_adb", False, str(e), "Install platform-tools or set android.adb_path in config.yaml.", False)


def check_ios() -> Check:
    if not _has_module("pymobiledevice3"):
        return Check("ios_pymobiledevice3", False, "not installed", "pip install pymobiledevice3", False)
    try:
        from core.ios import list_devices

        devices = list_devices(include_wifi=False)
        if devices:
            return Check("ios_pymobiledevice3", True, f"{len(devices)} USB iPhone(s)", required=False)
        return Check("ios_pymobiledevice3", False, "installed but no USB iPhone found", "Connect and trust an iPhone.", False)
    except Exception as e:
        return Check("ios_pymobiledevice3", False, str(e), "Check Apple Mobile Device Support and trust prompt.", False)


def run_checks(include_optional: bool = True) -> list[Check]:
    checks = [check_python(), check_python_packages(), check_config(), check_chrome()]
    if include_optional:
        checks.extend([check_android(), check_ios()])
    return checks


def _print_human(checks: list[Check]) -> None:
    required_failed = [c for c in checks if c.required and not c.ok]
    optional_failed = [c for c in checks if not c.required and not c.ok]

    print("RPA-Everything doctor\n")
    for check in checks:
        status = "OK" if check.ok else ("WARN" if not check.required else "FAIL")
        print(f"[{status}] {check.name}: {check.detail}")
        if not check.ok and check.fix:
            print(f"      fix: {check.fix}")

    print("\nNext step:")
    if required_failed:
        print("  Fix the FAIL items above, then rerun: python run.py harness/doctor")
    else:
        print('  Describe a workflow and export a first Skill:')
        print('  python run.py harness/agent -- --goal "Open the target system and do X" --dry-run')
        print('  python run.py harness/agent -- --goal "Open the target system and do X" --export skills/my_workflow.py')
    if optional_failed:
        print("\nOptional capabilities can stay WARN until you need that device type.")


def main():
    parser = argparse.ArgumentParser(description="Check whether RPA-Everything is ready to use.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--required-only", action="store_true", help="Skip Android/iPhone optional checks.")
    args = parser.parse_args(_argv())

    checks = run_checks(include_optional=not args.required_only)
    if args.json:
        print(json.dumps([c.__dict__ for c in checks], ensure_ascii=False, indent=2))
    else:
        _print_human(checks)

    if any(c.required and not c.ok for c in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
