"""desktop.py 纯逻辑部分的单元测试（不需要屏幕/pyautogui）。"""

import pytest

from core import desktop


@pytest.mark.unit
class TestPhysicalToLogical:
    @pytest.fixture(autouse=True)
    def reset_scale(self, monkeypatch):
        yield
        monkeypatch.setattr(desktop, "_SCALE_FACTOR", None)

    def test_retina_2x(self, monkeypatch):
        monkeypatch.setattr(desktop, "_SCALE_FACTOR", 2.0)
        assert desktop.physical_to_logical(2880, 1800) == (1440, 900)

    def test_no_scaling(self, monkeypatch):
        monkeypatch.setattr(desktop, "_SCALE_FACTOR", 1.0)
        assert desktop.physical_to_logical(500, 300) == (500, 300)

    def test_fractional_scaling(self, monkeypatch):
        # Windows 常见 125% 缩放
        monkeypatch.setattr(desktop, "_SCALE_FACTOR", 1.25)
        x, y = desktop.physical_to_logical(1000, 500)
        assert (x, y) == (800, 400)


@pytest.mark.unit
class TestHasCjk:
    def test_chinese(self):
        assert desktop._has_cjk("你好")

    def test_mixed(self):
        assert desktop._has_cjk("hello 世界")

    def test_ascii_only(self):
        assert not desktop._has_cjk("hello world 123")

    def test_empty(self):
        assert not desktop._has_cjk("")


@pytest.mark.unit
class TestResolve:
    def test_no_window_passthrough(self):
        assert desktop._resolve(10, 20, None) == (10, 20)

    def test_window_offset(self, monkeypatch):
        monkeypatch.setattr(desktop, "get_window_origin", lambda name: (100, 200))
        assert desktop._resolve(10, 20, "SomeApp") == (110, 220)
