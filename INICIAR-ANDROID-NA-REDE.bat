@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Bocali - Servidor para Android

REM Forca UTF-8 no Python para evitar falhas com acentos no Windows.
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

cls
echo ============================================================
echo              BOCALI - SERVIDOR NA REDE LOCAL
echo ============================================================
echo.
echo Esta janela deve permanecer ABERTA enquanto o celular usa o Bocali.
echo.

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"

if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
  echo [ERRO] Python nao foi encontrado neste computador.
  echo.
  echo Instale Python 3.11 ou superior e marque a opcao
  echo "Add python.exe to PATH" durante a instalacao.
  echo Depois feche esta janela e execute este arquivo novamente.
  echo.
  echo Para confirmar depois, abra o Prompt e execute: python --version
  goto :ERRO_FINAL
)

echo [1/5] Verificando Python...
%PY_CMD% -c "import sys; print('Python', sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3,11) else 2)"
if errorlevel 2 (
  echo [ERRO] O Bocali precisa do Python 3.11 ou superior.
  goto :ERRO_FINAL
)
if errorlevel 1 (
  echo [ERRO] Nao foi possivel executar o Python.
  goto :ERRO_FINAL
)

echo.
echo [2/5] Preparando ambiente do Bocali...
if not exist ".venv\Scripts\python.exe" (
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo [ERRO] Nao foi possivel criar o ambiente virtual .venv.
    goto :ERRO_FINAL
  )
)

echo.
echo [3/5] Instalando/verificando dependencias...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-hosted.txt
if errorlevel 1 (
  echo [ERRO] Falha ao instalar as dependencias do Bocali.
  echo Confira se o computador esta conectado a internet e tente novamente.
  goto :ERRO_FINAL
)

echo.
echo [4/5] Preparando configuracao local...
".venv\Scripts\python.exe" configure_local.py --show-codes
if errorlevel 1 (
  echo [ERRO] Falha ao preparar a configuracao local.
  goto :ERRO_FINAL
)

echo.
echo [5/5] Iniciando servidor...
echo.
echo IMPORTANTE:
echo - Esta janela deve ficar aberta.
echo - Computador e celular precisam estar na mesma rede Wi-Fi/LAN.
echo - Se o Firewall do Windows perguntar, permita somente em redes PRIVADAS.
echo - Para encerrar depois, pressione Ctrl+C nesta janela.
echo.

".venv\Scripts\python.exe" lan_server.py
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo O servidor foi encerrado.
) else (
  echo [ERRO] O servidor terminou com codigo %RC%.
)
goto :FIM

:ERRO_FINAL
echo.
echo ------------------------------------------------------------
echo O Bocali NAO foi iniciado. Leia a mensagem acima.
echo Se quiser, tire uma foto desta janela e envie no chat.
echo ------------------------------------------------------------

:FIM
echo.
pause
endlocal
