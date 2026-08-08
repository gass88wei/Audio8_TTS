@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem 探测可用的 python：py launcher 优先，其次 python
set "PYEXE="
where py >nul 2>nul && (
  for /f "delims=" %%i in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%i"
)
if not defined PYEXE (
  where python >nul 2>nul && for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%i"
)
if not defined PYEXE (
  echo [错误] 未找到 Python 3.11+，请先安装：https://www.python.org/downloads/
  pause
  exit /b 1
)

"%PYEXE%" --version >nul 2>nul || (
  echo [错误] Python 不可用：%PYEXE%
  pause
  exit /b 1
)

rem 初始化（装依赖 + 下模型，完成后秒过）
"%PYEXE%" "%~dp0init.py"
if errorlevel 1 (
  echo [错误] 初始化失败，请检查网络后重试
  pause
  exit /b 1
)

echo.
echo 开始运行 TUI 界面...
echo 提示：关闭本窗口即退出。
echo.
"%PYEXE%" "%~dp0tui_app.py"
pause