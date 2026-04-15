@echo off
chcp 65001 >nul
cls
echo ==========================================
echo  СБОРКА С ИКОНКОЙ
echo ==========================================

echo [1/5] Текущая директория: %cd%
echo.

echo [2/5] Поиск иконки...
if exist "icon.ico" (
    echo ✅ Иконка найдена: icon.ico
    dir icon.ico
) else (
    echo ❌ Иконка НЕ найдена!
    echo.
    echo Файлы в текущей папке:
    dir *.ico
    echo.
    echo Проверьте имя файла! Должно быть ТОЧНО icon.ico
    pause
    exit /b 1
)

echo.
echo [3/5] Очистка...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q *.spec

echo [4/5] Установка библиотек...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

echo [5/5] Сборка...
python -m PyInstaller --onefile --windowed ^
    --icon=icon.ico ^
    --name AI_Interviewer_Pro ^
    --hidden-import=faster_whisper ^
    --hidden-import=ctypes ^
    --collect-all=faster_whisper ^
    interview_app.py

echo.
if exist "dist\AI_Interviewer_Pro.exe" (
    for %%A in ("dist\AI_Interviewer_Pro.exe") do set size=%%~zA
    set /a size_mb=%size%/1048576
    echo ==========================================
    echo  ✅ ГОТОВО!
    echo  Файл: dist\AI_Interviewer_Pro.exe
    echo  Размер: %size_mb% MB
    echo ==========================================
) else (
    echo ❌ ОШИБКА сборки
    echo Проверьте логи выше
)
pause