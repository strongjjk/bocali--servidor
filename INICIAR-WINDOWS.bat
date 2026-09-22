@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Instale Python 3.11 ou superior. Este iniciador exige o comando py.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-hosted.txt
if errorlevel 1 (
  echo Nao foi possivel instalar as dependencias. Confira sua conexao.
  pause
  exit /b 1
)
.venv\Scripts\python.exe configure_local.py --show-codes
if errorlevel 1 (
  pause
  exit /b 1
)
echo Abra http://127.0.0.1:8000 no navegador DESTE computador.
echo A importacao de PDF funciona neste computador. Para outro aparelho, hospede o Bocali com HTTPS.
echo Nao fechar esta janela enquanto estiver testando.
.venv\Scripts\python.exe serve.py --local
pause
