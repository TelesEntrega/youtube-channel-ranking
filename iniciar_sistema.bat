@echo off
setlocal
title YouTube Ranking System Launcher

echo ===================================================
echo    YouTube Channel Ranking System - Launcher
echo ===================================================
echo.

:: 1. Verificar se Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python nao encontrado! Por favor instale o Python.
    pause
    exit /b
)

:: 2. Verificar/Criar ambiente virtual (opcional mas recomendado)
:: Se quiser usar venv, descomente as linhas abaixo
:: if not exist venv (
::    echo [i] Criando ambiente virtual...
::    python -m venv venv
:: )
:: call venv\Scripts\activate

:: 3. Instalar dependencias (basico)
if not exist "installed_dependencies.flag" (
    echo [i] Primeira execucao detectada. Instalando bibliotecas...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [X] Erro ao instalar dependencias.
        pause
        exit /b
    )
    echo done > installed_dependencies.flag
    echo [v] Dependencias instaladas!
)

:: 4. Verificar .env
if not exist .env (
    echo [!] Arquivo .env nao encontrado!
    if exist .env.example (
        copy .env.example .env
        echo [i] Arquivo .env criado a partir do exemplo.
        echo [!] POR FAVOR: Edite o arquivo .env e coloque sua YT_API_KEY.
        notepad .env
        pause
    )
)

:: 5. Iniciar Dashboard
echo.
echo [v] Iniciando sistema...
echo [i] O navegador abrira automaticamente.
echo [i] Pressione CTRL+C nesta janela para parar o servidor.
echo.

streamlit run app/main.py

pause
