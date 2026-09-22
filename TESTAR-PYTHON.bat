@echo off
setlocal
cd /d "%~dp0"
title Bocali - Diagnostico do Python
cls
echo BOCALI - DIAGNOSTICO DO COMPUTADOR
echo =================================
echo.
echo Procurando launcher "py":
where py 2>nul
if errorlevel 1 echo NAO ENCONTRADO
py --version 2>nul

echo.
echo Procurando comando "python":
where python 2>nul
if errorlevel 1 echo NAO ENCONTRADO
python --version 2>nul

echo.
echo Pasta atual:
echo %CD%
echo.
echo Arquivos principais:
if exist lan_server.py (echo OK - lan_server.py) else (echo FALTA - lan_server.py)
if exist requirements-hosted.txt (echo OK - requirements-hosted.txt) else (echo FALTA - requirements-hosted.txt)
if exist configure_local.py (echo OK - configure_local.py) else (echo FALTA - configure_local.py)
echo.
pause
endlocal
