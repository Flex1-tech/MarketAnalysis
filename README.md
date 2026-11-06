# 🌾 Prédiction des Prix des Denrées Agricoles au Bénin

Application web complète d'estimation des prix des céréales (maïs et riz) sur les marchés agricoles du Bénin à l'aide de modèles d'apprentissage automatique (**Random Forest** et **XGBoost**).

---

## 1. Architecture de Déploiement (Streamlit Cloud + Render + GitHub)

```text
┌─────────────────────────────────────────┐          HTTPS POST /predict          ┌──────────────────────────────────────────┐
│        FRONTEND (Interface Web)         │        + Header: X-API-Key            │           BACKEND (API REST)             │
│       Streamlit Community Cloud         │ ────────────────────────────────────► │             Render (Linux)               │
│  Entrypoint : frontend.py               │ ◄──────────────────────────────────── │  Entrypoint : app.Fast_api_price:app     │
│  Secrets    : st.secrets                │       JSON : { prix_predict }         │  Modèles    : RANDOM_FOREST.pkl          │
│               (BACKEND_URL, API_KEY,    │                                       │               XGBOST.pkl                 │
│                ADMIN_USER,              │                                       │  Port       : dynamique ($PORT)          │
│                ADMIN_PASSWORD_HASH)     │                                       │  Healthcheck: GET /health                │
└─────────────────────────────────────────┘                                       └──────────────────────────────────────────┘
                     ▲                                                                                 ▲
                     └───────────────────────────────────┬─────────────────────────────────────────────┘
                                                         │ Déploiement continu (CI/CD)
                                            ┌────────────┴────────────┐
                                            │   Dépôt Source GitHub   │
                                            └─────────────────────────┘
```

### Structure du dépôt
```text
projet data/
├── frontend.py                    # Point d'entrée principal pour Streamlit Community Cloud
├── app/                           # Package applicatif Python
│   ├── __init__.py
│   ├── Fast_api_price.py          # API Backend FastAPI (Render)
│   ├── frontend.py                # Logique de l'interface Streamlit
│   └── model/                     # Modèles ML pré-entraînés (suivis dans Git)
│       ├── RANDOM_FOREST.pkl      # RandomForestRegressor (8,26 Mo)
│       └── XGBOST.pkl             # XGBoost Booster (804 Ko)
├── .streamlit/
│   ├── config.toml                # Configuration serveur Streamlit
│   └── secrets.toml.example       # Modèle des secrets pour Streamlit Cloud
├── tests/
│   └── test_app.py                # Suite de tests automatisés
├── render.yaml                    # Blueprint de déploiement automatique pour Render
├── Dockerfile                     # Dockerfile Backend pour Render (supporte $PORT)
├── Dockerfile.backend             # Dockerfile Backend (Docker Compose)
├── Dockerfile.frontend            # Dockerfile Frontend (Docker Compose)
├── docker-compose.yml             # Orchestration locale multi-conteneurs
├── .env.example                   # Modèle des variables d'environnement
├── requirements.txt               # Dépendances Python
└── README.md                      # Documentation complète
```

---

## 2. Guide de Déploiement Pas-à-Pas

### Étape 1 : Publier le dépôt sur GitHub

1. Ouvrez un terminal à la racine du projet et initialisez Git :
   ```bash
   git init
   git branch -M main
   ```
2. Vérifiez que les fichiers sensibles (`.env`, `.streamlit/secrets.toml`, `.venv/`) sont bien ignorés et que les modèles (`app/model/*.pkl`) sont inclus :
   ```bash
   git status
   ```
3. Ajoutez les fichiers et créez le premier commit :
   ```bash
   git add .
   git commit -m "feat: prepare project for Render and Streamlit Community Cloud deployment"
   ```
4. Créez un nouveau dépôt (privé ou public) sur [GitHub](https://github.com/new), puis poussez le code :
   ```bash
   git remote add origin https://github.com/<votre-utilisateur>/<votre-depot>.git
   git push -u origin main
   ```

---

### Étape 2 : Déployer le Backend sur Render

Vous pouvez déployer sur [Render](https://dashboard.render.com/) via le fichier `render.yaml` (**Blueprint**) ou manuellement (**Web Service**) :

#### Option A — Via Blueprint (`render.yaml`)
1. Dans le Dashboard Render, cliquez sur **New +** > **Blueprint**.
2. Connectez votre dépôt GitHub.
3. Render détecte automatiquement `render.yaml` et vous demande la valeur de la variable secrète `API_KEY`.
4. Renseignez une clé secrète robuste (ex. générée avec `python -c "import secrets; print(secrets.token_urlsafe(32))"`), puis cliquez sur **Apply**.

#### Option B — Création manuelle d'un Web Service
1. Cliquez sur **New +** > **Web Service** et sélectionnez votre dépôt GitHub.
2. Configurez les paramètres suivants :
   - **Runtime** : `Python 3` (ou `Docker`)
   - **Build Command** : `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command** : `uvicorn app.Fast_api_price:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path** : `/health`
3. Dans la section **Environment Variables**, ajoutez :
   - `PYTHON_VERSION` = `3.11.0`
   - `API_KEY` = `<votre_cle_api_secrete>`

---

### Étape 3 : Récupérer et vérifier l'URL de l'API Render

1. Une fois le déploiement Render terminé (statut **Live**), copiez l'URL publique affichée en haut à gauche du service (ex. `https://agri-price-backend.onrender.com`).
2. Testez dans votre navigateur :
   - `https://agri-price-backend.onrender.com/health` -> doit afficher :
     ```json
     {"status":"healthy","models_loaded":{"random_forest":true,"xgboost":true}}
     ```
   - `https://agri-price-backend.onrender.com/docs` -> affiche la documentation interactive Swagger UI.

---

### Étape 4 : Déployer le Frontend sur Streamlit Community Cloud

1. Rendez-vous sur [share.streamlit.io](https://share.streamlit.io/) et connectez-vous avec votre compte GitHub.
2. Cliquez sur **Create app** (ou **New app**).
3. Renseignez :
   - **Repository** : `<votre-utilisateur>/<votre-depot>`
   - **Branch** : `main`
   - **Main file path** : `frontend.py` (ou `app/frontend.py`)
4. Cliquez sur **Advanced settings...** avant de lancer le déploiement pour configurer les secrets (voir Étape 5).

---

### Étape 5 : Configurer les Secrets

#### A. Sur Streamlit Community Cloud (`App settings > Secrets`)
Collez la configuration suivante au format TOML en remplaçant les valeurs :

```toml
BACKEND_URL = "https://agri-price-backend.onrender.com"
API_KEY = "votre-cle-api-secrete-identique-a-render"
ADMIN_USER = "admin"
ADMIN_PASSWORD_HASH = "votre-hash-sha256-64-caracteres"
```

> **Comment générer `ADMIN_PASSWORD_HASH` ?**
> Exécutez localement :
> ```bash
> python -c "import hashlib; print(hashlib.sha256('VotreMotDePasseSecret!'.encode('utf-8')).hexdigest())"
> ```

#### B. Sur Render (`Environment > Environment Variables`)
| Clé | Valeur |
| :--- | :--- |
| `API_KEY` | Exactement la même valeur que `API_KEY` configurée dans Streamlit Cloud |

---

### Étape 6 : Tester l'application en ligne

1. Ouvrez l'URL publique de votre application Streamlit (`https://<votre-app>.streamlit.app`).
2. **Test d'authentification** :
   - Essayez un mauvais mot de passe -> le message `Identifiants incorrects ❌` doit s'afficher.
   - Connectez-vous avec votre `ADMIN_USER` et le mot de passe correspondant à `ADMIN_PASSWORD_HASH`.
3. **Test de prédiction Random Forest** :
   - Sélectionnez **Random Forest**, choisissez un département, une ville, un marché, une marchandise et un mois (`1` à `12`), puis cliquez sur **Prédire le Prix**.
   - Vérifiez l'affichage du prix prédit en Francs CFA.
4. **Test de prédiction XGBoost** :
   - Basculez sur **XGBoost** et cliquez sur **Prédire le Prix**.
   - Vérifiez l'affichage du prix prédit.
   *(Note : Sur l'offre gratuite de Render, si l'API n'a reçu aucune requête depuis 15 minutes, le premier appel peut prendre 30 à 40 secondes le temps que le conteneur Render se réveille. Le timeout du frontend est configuré à 45 secondes pour gérer ce cas automatiquement).*

---

## 3. Exécution et Tests en Local

### Lancer les tests automatisés
```bash
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Lancer l'application localement
1. Vérifiez votre fichier `.env` (ou exécutez `2_run_app.bat` sous Windows).
2. Ou dans deux terminaux :
   ```bash
   # Terminal 1 : Backend FastAPI
   .\.venv\Scripts\uvicorn.exe app.Fast_api_price:app --host 127.0.0.1 --port 8000 --reload

   # Terminal 2 : Frontend Streamlit
   .\.venv\Scripts\streamlit.exe run frontend.py
   ```
