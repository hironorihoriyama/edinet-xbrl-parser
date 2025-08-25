@echo off
setlocal
rem --- move to project root (scripts/ の1つ上) ---
cd /d "%~dp0\.."

set "VENV=venv312"

rem --- make timestamped log path ---
for /f "tokens=1-6 delims=/:. " %%a in ("%date% %time%") do set "TS=%%c%%a%%b_%%d%%e%%f"
set "LOG=%CD%\setup_venv312_%TS%.log"
echo [INFO] Logging to "%LOG%"

rem --- create venv ---
py -3.12 -m venv "%VENV%"  >> "%LOG%" 2>&1 || goto :fail

call "%VENV%\Scripts\activate"
python -m pip install -U pip setuptools wheel  >> "%LOG%" 2>&1 || goto :fail

rem 本体をインストール（依存も入る）
pip install --only-binary=:all: .  >> "%LOG%" 2>&1 || goto :fail

rem ★ テスト用ツール（Pylance の警告抑止目的）
pip install -U pytest  >> "%LOG%" 2>&1 || goto :fail
python -c "import pytest; print('pytest', pytest.__version__)"  >> "%LOG%" 2>&1 || goto :fail

rem smoke check
python -c "from lxml import etree; import arelle, PIL, regex; print('OK', etree.LIBXML_VERSION)"  >> "%LOG%" 2>&1 || goto :fail

echo Setup finished. See "%LOG%"
endlocal & exit /b 0

:fail
echo [ERROR] Setup failed. See "%LOG%" for details.
endlocal & exit /b 1
