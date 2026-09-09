@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo Nao foi possivel criar o venv. Instale Python 3.11 ou superior.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cuda-runtime-cu12
python -m pip install -r requirements.txt
python -m pip install -e .

echo.
echo Iniciando Translator Live...
python -m translator
if errorlevel 1 pause
endlocal
