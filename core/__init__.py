# 刻意留空：不做子模块再导出。
# 按需 import core.browser / core.desktop / core.llm 等，
# 避免 import core.config 这类轻量操作连带加载 playwright/pyautogui。
