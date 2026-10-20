@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set "KIRA_PY=py -3") else (set "KIRA_PY=python")
%KIRA_PY% iniciar_laboratorio.py --con-windows
