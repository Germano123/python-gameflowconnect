@echo off
echo.
echo  ===================================================
echo   GameFlow Connect — Iniciando...
echo  ===================================================
echo.

:: Verifica se o venv existe
if not exist "venv\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual nao encontrado.
    echo Execute: python -m venv venv
    echo          venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Ativa o venv e executa
call venv\Scripts\activate.bat
python src\main.py
