# Exemple de Dockerfile sécurisé (multi-stage, non-root)
# ==============================================================================
# Build Stage
# ==============================================================================
FROM python:3.12-slim as builder

WORKDIR /app

# Sécurité: Installer uniquement les outils nécessaires pour compiler
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances 
# Note: On utilise pyproject.toml ou requirements.txt selon le projet
COPY requirements-locked.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements-locked.txt

# ==============================================================================
# Production Stage
# ==============================================================================
FROM python:3.12-slim

WORKDIR /app

# Création d'un utilisateur non-root (REM-005)
RUN groupadd -r tenxyte && useradd -r -g tenxyte tenxyte

# Installation des dépendances run-time (libpq pour PostgreSQL par ex)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copier les wheels construits (Multi-stage pour réduire les vulnérabilités)
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements-locked.txt .
RUN pip install --no-cache /wheels/*

# Copier l'application
COPY --chown=tenxyte:tenxyte src/ /app/src/

# Utiliser l'utilisateur non-root
USER tenxyte

# Exposer le port (Non-privilégié)
EXPOSE 8000

# Configuration des variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Démarrage avec gunicorn (à adapter selon le point d'entrée du projet réel)
# CMD ["gunicorn", "my_django_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
CMD ["python", "-m", "tenxyte"]
