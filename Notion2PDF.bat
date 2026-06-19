@echo off
REM Notion2PDF Windows launcher — double-click to run the GUI app.
REM 프로젝트 로컬 .venv의 pythonw로 GUI를 띄웁니다(콘솔 창 없이 실행).

setlocal
set "ROOT=%~dp0"
set "PYW=%ROOT%.venv\Scripts\pythonw.exe"
set "PY=%ROOT%.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo .venv를 찾을 수 없습니다. 먼저 scripts\setup_windows.ps1 을 실행해 설치하세요.
  pause
  exit /b 1
)

REM pythonw가 있으면 콘솔 없이, 없으면 일반 python으로 실행
if exist "%PYW%" (
  start "" "%PYW%" "%ROOT%notion2pdf_gui.py"
) else (
  "%PY%" "%ROOT%notion2pdf_gui.py"
)
endlocal
