@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem 用法：一键合成.bat "要合成的文本" [音色名]
set "TEXT=%~1"
set "VOICE=%~2"
if "%TEXT%"=="" (
  echo 用法：一键合成.bat "文本内容" [音色名]
  echo 例：一键合成.bat "你好世界" ci_voice
  pause
  exit /b 1
)
if "%VOICE%"=="" set "VOICE=default"

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

"%PYEXE%" "%~dp0init.py"
if errorlevel 1 (
  echo [错误] 初始化失败
  pause
  exit /b 1
)

"%PYEXE%" "%~dp0run_cli.py" --text "%TEXT%" --voice "%VOICE%"
pause