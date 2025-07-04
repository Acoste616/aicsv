#!/bin/bash

# Skrypt do uruchomienia aplikacji Streamlit

echo "🚀 Uruchamianie Streamlit Web Interface..."
echo "================================"

# Sprawdzenie czy streamlit jest zainstalowany
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit nie jest zainstalowany!"
    echo "Instaluję wymagane pakiety..."
    pip install -r requirements.txt
fi

# Sprawdzenie czy port 8501 jest wolny
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8501 jest zajęty. Zatrzymuję poprzednią instancję..."
    kill $(lsof -t -i:8501)
    sleep 2
fi

# Ustawienie zmiennych środowiskowych
export STREAMLIT_THEME_BASE="light"
export STREAMLIT_THEME_PRIMARY_COLOR="#4CAF50"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Informacja o przykładowym pliku
if [ -f "example_bookmarks.csv" ]; then
    echo "✅ Znaleziono przykładowy plik: example_bookmarks.csv"
    echo "   Możesz go użyć do testowania aplikacji"
fi

# Uruchomienie aplikacji
echo ""
echo "🌐 Aplikacja będzie dostępna pod adresem: http://localhost:8501"
echo ""
echo "Aby zatrzymać aplikację, naciśnij Ctrl+C"
echo "================================"

streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.address localhost \
    --server.fileWatcherType auto \
    --browser.gatherUsageStats false