@echo off
:: 启动带调试端口的 Chrome（Windows）
:: 使用独立 profile（%USERPROFILE%\.chrome-rpa-profile），与日常 Chrome 互不影响，可同时开两个窗口

set PROFILE_DIR=%USERPROFILE%\.chrome-rpa-profile
set CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe

:: 检查是否已在运行
curl -s http://127.0.0.1:9222/json/version >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Chrome 调试端口已就绪 ^(127.0.0.1:9222^)
    exit /b 0
)

echo [..] 启动 Chrome ^(调试模式^)...
start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%"

:: 等待就绪
set /a count=0
:wait
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:9222/json/version >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Chrome 已就绪 ^(127.0.0.1:9222^)
    echo      首次使用请在浏览器中登录各目标系统，之后免登录。
    exit /b 0
)
set /a count+=1
if %count% lss 15 goto wait

echo [ERR] Chrome 启动超时，请检查 Chrome 是否已安装
exit /b 1
