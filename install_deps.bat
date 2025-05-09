@echo off
echo Установка зависимостей из requirements.txt...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] При установке зависимостей произошёл сбой. Пожалуйста повторите попытку
    exit /b %ERRORLEVEL%
) else (
    echo [SUCCESS] Все зависимости успешно установлены! Можете запускать flask
)
pause
