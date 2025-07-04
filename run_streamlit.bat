@echo off
REM Skrypt do uruchomienia aplikacji Streamlit na Windows

echo.
echo 🚀 Uruchamianie Streamlit Web Interface...
echo ================================
echo.

REM Sprawdzenie czy streamlit jest zainstalowany
where streamlit >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Streamlit nie jest zainstalowany!
    echo Instaluje wymagane pakiety...
    pip install -r requirements.txt
)

REM Ustawienie zmiennych środowiskowych
set STREAMLIT_THEME_BASE=light
set STREAMLIT_THEME_PRIMARY_COLOR=#4CAF50
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

REM Informacja o przykładowym pliku
if exist "example_bookmarks.csv" (
    echo ✅ Znaleziono przykładowy plik: example_bookmarks.csv
    echo    Mozesz go uzyc do testowania aplikacji
)

REM Uruchomienie aplikacji
echo.
echo 🌐 Aplikacja bedzie dostepna pod adresem: http://localhost:8501
echo.
echo Aby zatrzymac aplikacje, nacisnij Ctrl+C
echo ================================
echo.

streamlit run streamlit_app.py ^
    --server.port 8501 ^
    --server.address localhost ^
    --server.fileWatcherType auto ^
    --browser.gatherUsageStats false