"""
桌面自动化：截图、鼠标键盘、窗口管理。
支持 macOS（screencapture + pyautogui/osascript）和 Windows（pywinauto）。

依赖安装：
  macOS:  brew install python@3.12 && python3.12 -m pip install pyautogui --break-system-packages
  Windows: pip install pywinauto pyautogui
"""

from __future__ import annotations

import platform
import subprocess
import tempfile

_IS_WINDOWS = platform.system() == "Windows"
_IS_MAC = platform.system() == "Darwin"

# pyautogui：macOS 需要 brew Python 3.12+，Windows/Linux 用当前 Python
# 除 ImportError 外，headless 环境（如 CI）下 pyautogui 会因无 DISPLAY 抛 KeyError 等异常
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.2
    _HAS_PYAUTOGUI = True
except Exception:
    _HAS_PYAUTOGUI = False

if _IS_WINDOWS:
    try:
        from pywinauto import Application as _WinApp
    except ImportError:
        pass


# ── 截图（跨平台）────────────────────────────────────────────────────

def screenshot(save_path: str = None) -> str:
    """截取全屏，返回保存路径。macOS 优先用 screencapture，其次 pyautogui。"""
    if save_path is None:
        fd, save_path = tempfile.mkstemp(suffix=".png")
        import os as _os
        _os.close(fd)

    if _IS_MAC:
        ret = subprocess.run(["screencapture", "-x", save_path], capture_output=True)
        if ret.returncode == 0:
            return save_path
        # screencapture 失败时降级到 pyautogui
    if _HAS_PYAUTOGUI:
        pyautogui.screenshot(save_path)
        return save_path

    raise RuntimeError(
        "截图失败：macOS 请确认终端已授权「屏幕录制」权限，"
        "或安装 pyautogui（brew python3.12 -m pip install pyautogui --break-system-packages）"
    )


# ── 鼠标操作（跨平台）────────────────────────────────────────────────

def click(x: int, y: int, window: str | None = None):
    """点击坐标。window 指定应用名时坐标为窗口相对位置，否则为屏幕绝对坐标。"""
    _require_pyautogui()
    ax, ay = _resolve(x, y, window)
    pyautogui.click(ax, ay)


def double_click(x: int, y: int, window: str | None = None):
    _require_pyautogui()
    ax, ay = _resolve(x, y, window)
    pyautogui.doubleClick(ax, ay)


def right_click(x: int, y: int, window: str | None = None):
    _require_pyautogui()
    ax, ay = _resolve(x, y, window)
    pyautogui.rightClick(ax, ay)


def move_to(x: int, y: int, window: str | None = None):
    _require_pyautogui()
    ax, ay = _resolve(x, y, window)
    pyautogui.moveTo(ax, ay)


# 覆盖小幅漂移（±5%/±10%/±15%）以及常见跨机器 DPI 缩放比（100%/125%/150%/200% 两两相除
# 得到的比例，如 0.8、1.25、0.67、1.5），换机器或系统缩放设置不同时也有机会匹配上。
_MULTI_SCALES = (1.0, 0.95, 1.05, 0.9, 1.1, 0.85, 1.15, 0.8, 1.25, 0.67, 1.5)


def _cv2_imread_unicode(path: str):
    """Read image files with non-ASCII paths on Windows."""
    try:
        import cv2
        import numpy as np
    except Exception:
        return None
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def _cv2_imwrite_unicode(path: str, image) -> bool:
    try:
        import cv2
    except Exception:
        return False
    suffix = "." + path.rsplit(".", 1)[-1] if "." in path else ".png"
    ok, data = cv2.imencode(suffix, image)
    if not ok:
        return False
    data.tofile(path)
    return True


def _locate_on_screen_cv2(template_path: str, confidence: float = 0.85, multi_scale: bool = True):
    try:
        import cv2
        import numpy as np
    except Exception:
        return None

    template = _cv2_imread_unicode(template_path)
    if template is None:
        return None
    shot = pyautogui.screenshot()
    screen = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)

    best = None
    scales = _MULTI_SCALES if multi_scale else (1.0,)
    for scale in scales:
        if scale == 1.0:
            candidate = template
        else:
            h, w = template.shape[:2]
            candidate = cv2.resize(template, (max(1, round(w * scale)), max(1, round(h * scale))))
        h, w = candidate.shape[:2]
        if h > screen.shape[0] or w > screen.shape[1]:
            continue
        res = cv2.matchTemplate(screen, candidate, cv2.TM_CCOEFF_NORMED)
        _, score, _, point = cv2.minMaxLoc(res)
        if score >= confidence and (best is None or score > best[0]):
            best = (score, point[0], point[1], w, h)
    if best is None:
        return None
    _, x, y, w, h = best
    return (x, y, w, h)


def locate_on_screen(template_path: str, confidence: float = 0.85, multi_scale: bool = True):
    """
    在当前屏幕上定位模板，返回 pyscreeze Box 或 None。
    multi_scale=True 时按 _MULTI_SCALES 依次缩放模板再匹配，容忍分辨率/缩放/DPI 的漂移
    ——模板是在标定时的分辨率下截的，换机器或系统缩放比例变化后精确匹配容易失败。
    """
    _require_pyautogui()
    loc = _locate_on_screen_cv2(template_path, confidence=confidence, multi_scale=multi_scale)
    if loc:
        return loc

    from PIL import Image

    scales = _MULTI_SCALES if multi_scale else (1.0,)
    original = None
    for scale in scales:
        if scale == 1.0:
            candidate = template_path
        else:
            if original is None:
                original = Image.open(template_path)
            w, h = original.size
            candidate = original.resize((max(1, round(w * scale)), max(1, round(h * scale))))
        try:
            loc = pyautogui.locateOnScreen(candidate, confidence=confidence)
        except pyautogui.ImageNotFoundException:
            loc = None
        if loc:
            return loc
    return None


def locate_and_click(
    template_path: str,
    confidence: float = 0.85,
    double: bool = False,
    timeout: float = 5.0,
    multi_scale: bool = True,
) -> bool:
    """
    在当前屏幕用图像模板定位元素并点击其中心，取代"截图猜坐标"。
    适合样式固定、内容不变的 UI 元素（按钮、图标、导航项）。
    找到并点击返回 True；超时未找到返回 False（调用方应据此判断是否继续/报错，而非静默重试）。
    """
    import time as _time

    deadline = _time.time() + timeout
    while _time.time() < deadline:
        loc = locate_on_screen(template_path, confidence=confidence, multi_scale=multi_scale)
        if loc:
            center = pyautogui.center(loc)
            lx, ly = physical_to_logical(center.x, center.y)
            if double:
                pyautogui.doubleClick(lx, ly)
            else:
                pyautogui.click(lx, ly)
            return True
        _time.sleep(0.3)
    return False


# ── 键盘操作（跨平台）────────────────────────────────────────────────

def type_text(text: str):
    """输入文字。中文走剪贴板粘贴，英文直接 typewrite。"""
    if _has_cjk(text):
        _paste_text(text)
    else:
        _require_pyautogui()
        pyautogui.typewrite(text, interval=0.05)


def hotkey(*keys: str):
    """发送快捷键，如 hotkey('command', 'k')。"""
    _require_pyautogui()
    pyautogui.hotkey(*keys)


def press(key: str):
    """按单个键，如 press('enter')、press('escape')。"""
    _require_pyautogui()
    pyautogui.press(key)


# ── 窗口坐标工具 ────────────────────────────────────────────────────

def get_window_origin(app_name: str) -> tuple[int, int]:
    """返回指定应用窗口左上角的屏幕坐标（逻辑像素）。macOS 用 System Events，
    Windows 用 pygetwindow 按标题匹配。都找不到时返回 (0, 0)。"""
    if _IS_WINDOWS:
        try:
            import pygetwindow as gw
            wins = gw.getWindowsWithTitle(app_name)
            if wins:
                return wins[0].left, wins[0].top
        except Exception:
            pass
        return (0, 0)
    if not _IS_MAC:
        return (0, 0)
    script = f'''
    tell application "System Events"
        tell process "{app_name}"
            set b to position of window 1
            return ((item 1 of b) as text) & "," & ((item 2 of b) as text)
        end tell
    end tell
    '''
    try:
        out = subprocess.check_output(["osascript", "-e", script], stderr=subprocess.DEVNULL)
        x, y = out.decode().strip().split(",")
        return int(x), int(y)
    except Exception:
        return (0, 0)


def _resolve(x: int, y: int, window: str | None) -> tuple[int, int]:
    """将窗口相对坐标转换为屏幕绝对坐标。window=None 时直接返回原值。
    注意：这里的 x/y 约定为 pyautogui 逻辑像素（即 pyautogui.size() 的坐标系），
    不是 screenshot()/locate_and_click() 用的物理像素——调用方需自行
    用 physical_to_logical() 换算，坐标系差异详见 ARCHITECTURE.md。"""
    if window is None:
        return x, y
    wx, wy = get_window_origin(window)
    return wx + x, wy + y


def _scale_factor() -> float:
    """
    screenshot() 在 Retina Mac 上返回物理像素尺寸（如 2880x1800），
    但 pyautogui 点击用的是逻辑像素（如 1440x900，即 pyautogui.size()）。
    两者通常按整数倍缩放（Retina 常见 2x）。首次调用时探测一次并缓存。
    """
    global _SCALE_FACTOR
    if _SCALE_FACTOR is None:
        _SCALE_FACTOR = 1.0
        if _HAS_PYAUTOGUI:
            try:
                shot_w, _ = pyautogui.screenshot().size
                logical_w, _ = pyautogui.size()
                if logical_w:
                    _SCALE_FACTOR = shot_w / logical_w
            except Exception:
                pass
    return _SCALE_FACTOR


_SCALE_FACTOR: float | None = None


def physical_to_logical(x: int, y: int) -> tuple[float, float]:
    """
    截图物理像素坐标（screenshot()/locate_and_click() 所在坐标系）
    → pyautogui 点击用的逻辑坐标（click()/move_to() 所在坐标系）。
    LLM 从 desktop_screenshot 截图里读出的坐标属于物理像素系，
    传给 click() 前必须经过这层转换，否则 Retina 屏幕上点击位置会偏移。
    """
    scale = _scale_factor()
    return x / scale, y / scale


# ── 窗口管理（macOS + Windows）──────────────────────────────────────

def activate_app(app_name: str):
    """将指定应用切换到前台。用 System Events 按进程名寻址，比 `tell application X to activate`
    更可靠——后者依赖应用的 AppleScript 词典名，某些应用（如飞书）对不上进程名会报错。"""
    if _IS_MAC:
        subprocess.run([
            "osascript", "-e",
            f'tell application "System Events" to set frontmost of process "{app_name}" to true',
        ])
    elif _IS_WINDOWS and _HAS_PYAUTOGUI:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(app_name)
        if wins:
            wins[0].activate()


def open_app(path: str):
    """启动本地应用。"""
    if _IS_MAC:
        subprocess.run(["open", path])
    else:
        subprocess.Popen(path)


# ── Windows UI Automation（仅 Windows）──────────────────────────────
#
# 已知坑（尚未实现，留给以后需要按窗口句柄截图时参考）：Windows 上如果要截取指定
# hwnd 的窗口内容（而不是全屏 screenshot()），优先用 PrintWindow(PW_RENDERFULLCONTENT)，
# 桌面DC BitBlt 仅作降级方案——某些窗口的子区域是硬件加速/分层渲染的（如内嵌头像、
# 视频控件），BitBlt 截不到会透出背后桌面像素，但图不会全黑，容易被误判成"截图成功"。
# 当前 screenshot() 在 Windows 上直接用 pyautogui.screenshot()（全屏截图），
# 还没有按 hwnd 截取子窗口的实现，真到需要时再加。

def win_connect(title_keyword: str = None, path: str = None):
    """连接到 Windows 原生应用，返回 pywinauto Application 对象。"""
    if not _IS_WINDOWS:
        raise RuntimeError("win_connect 仅支持 Windows")
    if path:
        return _WinApp(backend="uia").start(path)
    return _WinApp(backend="uia").connect(title_re=f".*{title_keyword}.*")


def win_find_element(title_keyword: str, control_title: str = None, control_type: str = None):
    if not _IS_WINDOWS:
        raise RuntimeError("win_find_element 仅支持 Windows")
    app = win_connect(title_keyword=title_keyword)
    dlg = app.top_window()
    kwargs = {}
    if control_title:
        kwargs["title"] = control_title
    if control_type:
        kwargs["control_type"] = control_type
    return dlg.child_window(**kwargs)


def win_list_elements(title_keyword: str) -> list:
    if not _IS_WINDOWS:
        return []
    app = win_connect(title_keyword=title_keyword)
    dlg = app.top_window()
    elements = []
    for el in dlg.descendants():
        try:
            elements.append({
                "title": el.window_text(),
                "type": el.element_info.control_type,
                "rect": str(el.rectangle()),
            })
        except Exception:
            pass
    return elements


# ── 内部工具 ─────────────────────────────────────────────────────────

def _require_pyautogui():
    if not _HAS_PYAUTOGUI:
        raise RuntimeError(
            "pyautogui 未安装。macOS 请运行：\n"
            "  /opt/homebrew/bin/python3.12 -m pip install pyautogui --break-system-packages"
        )


def _has_cjk(text: str) -> bool:
    return any('一' <= c <= '鿿' or '　' <= c <= 'ヿ' for c in text)


def _paste_text(text: str):
    """通过剪贴板粘贴（解决中文 typewrite 乱码问题）。"""
    if _IS_MAC:
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
        _require_pyautogui()
        pyautogui.hotkey("command", "v")
    elif _IS_WINDOWS:
        import pyperclip
        pyperclip.copy(text)
        _require_pyautogui()
        pyautogui.hotkey("ctrl", "v")
    else:
        # 静默返回会让调用方误以为输入成功
        raise NotImplementedError("剪贴板粘贴暂不支持当前平台（仅 macOS / Windows）")
