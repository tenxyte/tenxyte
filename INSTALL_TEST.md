# Instructions d'Installation pour Test

## 1. Activer l'environnement du projet test

```bash
conda activate tenxyte_test_conda_env
```

## 2. Installer le package en mode éditable

```bash
cd C:\Users\bobop\Documents\own\tenxyte\packages\tenxyte-auth
pip install -e .
```

Cette commande va :
- Installer toutes les dépendances (Django, DRF, PyJWT, pyotp, etc.)
- Créer un lien symbolique vers le package pour le développement

## 3. Vérifier l'installation

```bash
python -c "import tenxyte; print(tenxyte.__version__)"
```

Devrait afficher : `0.0.8`

## 4. Aller dans le projet test et faire les migrations

```bash
cd C:\Users\bobop\Documents\own\tenxyte_test
python manage.py migrate
```

## 5. Créer une application (credentials)

```bash
python manage.py shell
```

Puis :
```python
from tenxyte.models import Application

app = Application.objects.create(
    name="Test Frontend",
    description="Application de test"
)

print(f"Access Key: {app.access_key}")
print(f"Access Secret: {app.access_secret}")
```

**⚠️ IMPORTANT :** Sauvegarder le `access_secret` car il sera hashé après le save !

## 6. Lancer le serveur

```bash
python manage.py runserver
```

## 7. Tester les endpoints

### Vérifier l'API
```bash
curl http://localhost:8000/api/auth/password/requirements/
```

### Register un utilisateur
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "X-Access-Key: <your_access_key>" \
  -H "X-Access-Secret: <your_access_secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "first_name": "Test",
    "last_name": "User"
  }'
```

## Dépannage

### Erreur "No module named 'tenxyte'"
- Vérifier que vous êtes dans le bon environnement : `conda activate tenxyte_test_conda_env`
- Réinstaller : `pip install -e C:\Users\bobop\Documents\own\tenxyte\packages\tenxyte-auth`

### Erreur lors de l'import de models
- Vérifier que tous les fichiers sont bien copiés dans `src/tenxyte/`
- Vérifier que `__init__.py` existe dans chaque sous-dossier

### Erreur "cannot import name 'auth_settings'"
- Vérifier que `conf.py` existe bien dans `src/tenxyte/`
