#!/bin/bash
# 启动带调试端口的 Chrome（macOS）
# 使用独立 profile，首次需要登录，之后免登录

PROFILE_DIR="$HOME/.chrome-rpa-profile"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 检查是否已是真正的 DevTools server（返回 Browser 字段）
if curl -s http://127.0.0.1:9222/json/version 2>/dev/null | grep -q '"Browser"'; then
    echo "✅ Chrome 调试端口已就绪（127.0.0.1:9222）"
    exit 0
fi

echo "🚀 启动 Chrome（调试模式，独立 profile）..."
"$CHROME" \
    --remote-debugging-port=9222 \
    --user-data-dir="$PROFILE_DIR" \
    > /dev/null 2>&1 &

# 等待就绪
for i in $(seq 1 20); do
    sleep 0.5
    if curl -s http://127.0.0.1:9222/json/version > /dev/null 2>&1; then
        echo "✅ Chrome 已就绪（127.0.0.1:9222）"
        echo "   首次使用请在浏览器中登录各目标系统，之后免登录。"
        exit 0
    fi
done

echo "❌ Chrome 启动超时，请检查 Chrome 是否已安装"
exit 1
