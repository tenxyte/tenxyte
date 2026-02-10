# Guide de Configuration Base de Données - Tenxyte

Tenxyte est compatible avec toutes les bases de données supportées par Django :
- **SQLite** (développement)
- **PostgreSQL** (production recommandée)
- **MySQL/MariaDB**
- **MongoDB** (via django-mongodb-backend)

---

## 🗄️ SQLite (Par Défaut)

Parfait pour le développement et les tests.

### Configuration

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### Installation

```bash
# Aucune dépendance supplémentaire
python manage.py migrate
```

**✅ Avantages :** Zero configuration, idéal pour dev
**❌ Inconvénients :** Pas adapté pour production

---

## 🐘 PostgreSQL (Recommandé Production)

Base de données relationnelle robuste et performante.

### Installation des dépendances

```bash
pip install psycopg2-binary
# OU pour compiler depuis les sources (plus performant) :
pip install psycopg2
```

### Configuration

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tenxyte_db',
        'USER': 'postgres',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Setup PostgreSQL

#### Windows (avec PostgreSQL installé)
```bash
# Ouvrir psql
psql -U postgres

# Créer la base de données
CREATE DATABASE tenxyte_db;
CREATE USER tenxyte_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE tenxyte_db TO tenxyte_user;
\q
```

#### Linux/macOS
```bash
sudo -u postgres psql
CREATE DATABASE tenxyte_db;
CREATE USER tenxyte_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE tenxyte_db TO tenxyte_user;
\q
```

#### Docker (Rapide)
```bash
docker run -d \
  --name postgres_tenxyte \
  -e POSTGRES_DB=tenxyte_db \
  -e POSTGRES_USER=tenxyte_user \
  -e POSTGRES_PASSWORD=secure_password \
  -p 5432:5432 \
  postgres:16
```

### Migration

```bash
python manage.py migrate
```

**✅ Avantages :** Robuste, performant, JSONB natif, très bien supporté
**❌ Inconvénients :** Nécessite un serveur PostgreSQL

---

## 🐬 MySQL / MariaDB

Base de données relationnelle populaire.

### Installation des dépendances

```bash
pip install mysqlclient
# OU
pip install pymysql
```

Si vous utilisez `pymysql`, ajoutez dans `settings.py` ou `manage.py` :
```python
import pymysql
pymysql.install_as_MySQLdb()
```

### Configuration

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'tenxyte_db',
        'USER': 'root',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}
```

### Setup MySQL

#### Windows/Linux/macOS
```bash
mysql -u root -p

CREATE DATABASE tenxyte_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'tenxyte_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON tenxyte_db.* TO 'tenxyte_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### Docker (MariaDB)
```bash
docker run -d \
  --name mariadb_tenxyte \
  -e MYSQL_DATABASE=tenxyte_db \
  -e MYSQL_USER=tenxyte_user \
  -e MYSQL_PASSWORD=secure_password \
  -e MYSQL_ROOT_PASSWORD=root_password \
  -p 3306:3306 \
  mariadb:11
```

### Migration

```bash
python manage.py migrate
```

**✅ Avantages :** Largement utilisé, bon support
**❌ Inconvénients :** Moins de fonctionnalités avancées que PostgreSQL

---

## 🍃 MongoDB

Base de données NoSQL orientée documents.

### Installation des dépendances

```bash
pip install djongo
# OU (backend officiel MongoDB)
pip install django-mongodb-backend
```

### Configuration avec django-mongodb-backend (Recommandé)

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_backend',
        'NAME': 'tenxyte_db',
        'HOST': 'localhost',
        'PORT': 27017,
        'USER': '',  # Optionnel
        'PASSWORD': '',  # Optionnel
        'OPTIONS': {
            'authSource': 'admin',  # Si authentification
        }
    }
}

# IMPORTANT: Utiliser les apps MongoDB-compatibles pour admin, auth, contenttypes
INSTALLED_APPS = [
    # Remplacer les apps Django standards par les versions MongoDB
    'django_mongodb_backend.apps.MongoAdminConfig',
    'django_mongodb_backend.apps.MongoAuthConfig',
    'django_mongodb_backend.apps.MongoContentTypesConfig',

    # Apps Django standards
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Tenxyte
    'tenxyte',

    # Vos apps
]
```

### Setup MongoDB

#### Installation MongoDB Community

**Windows :**
1. Télécharger : https://www.mongodb.com/try/download/community
2. Installer MongoDB Community Server
3. MongoDB sera accessible sur `mongodb://localhost:27017`

**Linux (Ubuntu/Debian) :**
```bash
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
```

**macOS (Homebrew) :**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

#### Docker (Rapide)
```bash
docker run -d \
  --name mongodb_tenxyte \
  -e MONGO_INITDB_DATABASE=tenxyte_db \
  -p 27017:27017 \
  mongo:7
```

#### Avec authentification (Production)
```bash
docker run -d \
  --name mongodb_tenxyte \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=secure_password \
  -e MONGO_INITDB_DATABASE=tenxyte_db \
  -p 27017:27017 \
  mongo:7
```

Puis dans `settings.py` :
```python
DATABASES = {
    'default': {
        'ENGINE': 'django_mongodb_backend',
        'NAME': 'tenxyte_db',
        'HOST': 'localhost',
        'PORT': 27017,
        'USER': 'admin',
        'PASSWORD': 'secure_password',
        'OPTIONS': {
            'authSource': 'admin',
            'authMechanism': 'SCRAM-SHA-256',
        }
    }
}
```

### Migration

```bash
python manage.py migrate
```

**✅ Avantages :** Flexible, scalable, schéma dynamique
**❌ Inconvénients :** Nécessite django-mongodb-backend

---

## 🐳 Docker Compose (Toutes les DB)

Fichier `docker-compose.yml` pour tester toutes les bases :

```yaml
version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: tenxyte_db
      POSTGRES_USER: tenxyte_user
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # MySQL
  mysql:
    image: mysql:8
    environment:
      MYSQL_DATABASE: tenxyte_db
      MYSQL_USER: tenxyte_user
      MYSQL_PASSWORD: secure_password
      MYSQL_ROOT_PASSWORD: root_password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  # MongoDB
  mongodb:
    image: mongo:7
    environment:
      MONGO_INITDB_DATABASE: tenxyte_db
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db

volumes:
  postgres_data:
  mysql_data:
  mongodb_data:
```

Lancer :
```bash
docker-compose up -d
```

---

## 🔄 Changer de Base de Données

Si vous changez de base de données :

1. **Modifier `settings.py`** avec la nouvelle configuration
2. **Installer les dépendances** nécessaires
3. **Réinitialiser les migrations** :
   ```bash
   # Supprimer l'ancienne DB
   rm db.sqlite3  # Si SQLite

   # Recréer la nouvelle DB (voir sections ci-dessus)

   # Relancer les migrations
   python manage.py migrate
   ```

---

## 📊 Comparaison Rapide

| Base de Données | Facilité Setup | Performance | Production | NoSQL |
|----------------|----------------|-------------|------------|-------|
| **SQLite**     | ⭐⭐⭐⭐⭐        | ⭐⭐          | ❌         | ❌    |
| **PostgreSQL** | ⭐⭐⭐          | ⭐⭐⭐⭐⭐     | ✅✅       | ❌    |
| **MySQL**      | ⭐⭐⭐          | ⭐⭐⭐⭐       | ✅         | ❌    |
| **MongoDB**    | ⭐⭐⭐⭐         | ⭐⭐⭐⭐       | ✅         | ✅    |

### Recommandations

- **Développement local** : SQLite (zéro config)
- **Production API/Web** : PostgreSQL (robuste, complet)
- **Besoin NoSQL** : MongoDB (flexible, scalable)
- **Compatibilité maximale** : MySQL (largement supporté)

---

## 🆘 Dépannage

### Erreur "No module named 'psycopg2'"
```bash
pip install psycopg2-binary
```

### Erreur "No module named 'MySQLdb'"
```bash
pip install mysqlclient
```

### Erreur "No module named 'django_mongodb_backend'"
```bash
pip install django-mongodb-backend
```

### MongoDB : "Authentication failed"
Vérifier `authSource` dans les OPTIONS :
```python
'OPTIONS': {
    'authSource': 'admin',  # ou 'tenxyte_db'
}
```

### PostgreSQL : "Peer authentication failed"
Modifier `/etc/postgresql/XX/main/pg_hba.conf` :
```
local   all   all   md5
```

---

## 📚 Ressources

- [Django Databases](https://docs.djangoproject.com/en/5.0/ref/databases/)
- [PostgreSQL Setup](https://www.postgresql.org/download/)
- [MySQL Setup](https://dev.mysql.com/downloads/)
- [MongoDB Setup](https://www.mongodb.com/docs/manual/installation/)
- [django-mongodb-backend](https://github.com/mongodb-labs/django-mongodb-backend)
