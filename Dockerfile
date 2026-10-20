# Dockerfile de l'assistant Randoneo — application + serveur MCP dans le même conteneur.
#
#   docker build -t randoneo-app .
#   docker run --rm -p 7860:7860 --env-file .env \
#     -v "$PWD/.streamlit:/app/.streamlit:ro" randoneo-app

# Python 3.12 (le minimum est 3.11 ; en 3.10, la validation humaine échoue).
FROM python:3.12-slim

# Les logs sortent sans tampon (sinon ils n'arrivent qu'après coup, ou jamais).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Dossier de travail.
WORKDIR /app

# Dépendances AVANT le code (pour profiter du cache Docker).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code de l'application.
COPY . .

# Utilisateur non-root (une faille dans une dépendance ne s'exécute pas en root).
RUN useradd --create-home --uid 1000 appuser
USER appuser

# Port documenté + contrôle de santé.
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/_stcore/health')"

# Commande de démarrage : Streamlit écoute sur 0.0.0.0:7860.
CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=7860", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]