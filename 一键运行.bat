@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_here.ps1"
if errorlevel 1 (
    echo.
    echo 启动失败，请看上面的原因。
    pause
)
