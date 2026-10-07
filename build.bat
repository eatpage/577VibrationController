@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYEXE=C:\Users\guaiy\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

echo 使用解释器: %PYEXE%
echo 开始打包，首次构建大约需要 1~3 分钟...
echo.

"%PYEXE%" build.py %*

echo.
echo 打包流程结束。
pause
