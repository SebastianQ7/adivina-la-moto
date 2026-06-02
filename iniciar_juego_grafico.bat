@echo off
REM ============================================================
REM   Lanzador GRAFICO de "Adivina Quien - Motos"
REM   Abre: servidor (consola) + 2 ventanas graficas (Ana y Beto)
REM ============================================================
chcp 65001 >nul
title Lanzador grafico - Adivina Quien (Motos)
cd /d "%~dp0"

REM --- Detectar el comando de Python disponible (python o py) ---
set "PY=python"
where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] No se encontro Python en el PATH.
        echo Instala Python desde https://www.python.org/ y marca "Add Python to PATH".
        pause
        exit /b
    )
    set "PY=py"
)

echo.
echo Iniciando el SERVIDOR...
start "Servidor - Adivina Quien" cmd /k "chcp 65001 >nul && %PY% server.py"

echo Esperando 2 segundos a que el servidor arranque...
timeout /t 2 /nobreak >nul

echo Abriendo ventana grafica JUGADOR 1 (Ana)...
start "" %PY% gui_client.py Ana

echo Abriendo ventana grafica JUGADOR 2 (Beto)...
start "" %PY% gui_client.py Beto

echo.
echo Listo. Se abrio el servidor (consola) y 2 ventanas del juego.
timeout /t 3 /nobreak >nul
exit /b
