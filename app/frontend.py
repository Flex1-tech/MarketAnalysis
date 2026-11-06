import hashlib
import hmac
import os
from pathlib import Path
import requests
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


def load_env_file(env_path: Path) -> None:
    """Charge un fichier .env local sans dépendance externe s'il existe."""
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file(PROJECT_ROOT / ".env")
load_env_file(BASE_DIR / ".env")


def get_secret(key: str, default: str = "") -> str:
    """
    Récupère une configuration ou un secret en priorité depuis `st.secrets`
    (Streamlit Community Cloud), puis depuis les variables d'environnement (`os.environ`).
    """
    try:
        if key in st.secrets:
            val = st.secrets[key]
            if val is not None:
                return str(val).strip()
    except Exception:
        # Ignore l'absence de fichier secrets.toml en environnement local/test
        pass
    return os.getenv(key, default).strip()


def get_predict_url() -> str:
    """Construit l'URL complète de l'endpoint /predict à partir de BACKEND_URL."""
    raw_url = get_secret("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    if not raw_url:
        raw_url = "http://127.0.0.1:8000"
    if raw_url.endswith("/predict"):
        return raw_url
    return f"{raw_url}/predict"


def get_request_timeout() -> float:
    """
    Retourne le timeout HTTP en secondes (45s par défaut pour tolérer le
    réveil / cold-start éventuel d'une instance Render).
    """
    raw_timeout = get_secret("BACKEND_TIMEOUT", "45")
    try:
        return float(raw_timeout)
    except ValueError:
        return 45.0


def verify_credentials(username: str, password: str) -> bool:
    """
    Vérifie les identifiants de manière sécurisée (comparaison en temps constant)
    à partir de ADMIN_USER et ADMIN_PASSWORD_HASH (SHA-256 hex) issus de st.secrets
    ou des variables d'environnement.
    """
    if not username or not password:
        return False

    expected_user = get_secret("ADMIN_USER") or get_secret("APP_ADMIN_USERNAME")
    expected_hash = (
        get_secret("ADMIN_PASSWORD_HASH") or get_secret("APP_ADMIN_PASSWORD_HASH")
    ).lower()
    expected_plain = get_secret("ADMIN_PASSWORD") or get_secret("APP_ADMIN_PASSWORD")

    if not expected_user or (not expected_hash and not expected_plain):
        return False

    user_ok = hmac.compare_digest(username.strip(), expected_user)

    if expected_hash:
        if expected_hash.startswith("sha256:"):
            expected_hash = expected_hash.split("sha256:", 1)[1]
        candidate_hash = hashlib.sha256(password.encode("utf-8")).hexdigest().lower()
        password_ok = hmac.compare_digest(candidate_hash, expected_hash)
    else:
        password_ok = hmac.compare_digest(password, expected_plain)

    return user_ok and password_ok


# Authentification
def login():
    st.title("🔐 Connexion")
    st.subheader("Veuillez entrer vos identifiants")

    admin_user = get_secret("ADMIN_USER") or get_secret("APP_ADMIN_USERNAME")
    admin_hash = (
        get_secret("ADMIN_PASSWORD_HASH")
        or get_secret("APP_ADMIN_PASSWORD_HASH")
        or get_secret("ADMIN_PASSWORD")
        or get_secret("APP_ADMIN_PASSWORD")
    )

    if not admin_user or not admin_hash:
        st.warning(
            "⚠️ L'authentification n'est pas configurée. "
            "Veuillez définir `ADMIN_USER` et `ADMIN_PASSWORD_HASH` dans les Secrets Streamlit Cloud (`st.secrets`) ou `.env`."
        )

    username = st.text_input("Nom d'utilisateur", placeholder="Entrez votre nom")
    password = st.text_input("Mot de passe", type="password", placeholder="Entrez votre mot de passe")

    if st.button("Se connecter"):
        if verify_credentials(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Identifiants incorrects ❌")


# Page de prédiction
def predicteur():
    st.title("🌾 Estimation des Prix sur les Marchés Agricoles")

    # Choix du modèle
    st.write("### ⚙️ Configuration du Modèle")
    modele_choisi = st.radio("Sélectionnez l'algorithme :", ["Random Forest", "XGBoost"])
    st.divider()

    # Listes exactes basées sur votre encodage (l'index correspond au code numérique)
    liste_departements = ['Alibori', 'Atakora', 'Atlantique', 'Borgou', 'Collines', 'Couffo', 'Donga', 'Littoral', 'Mono', 'Oueme', 'Plateau', 'Zou']
    
    liste_villes = ['Abomey', 'Abomey-calavi', 'Adja-ouere', 'Adjohoun', 'Allada', 'Aplahoue', 'Banikoara', 'Bassila', 'Bembereke', 'Bohicon', 'Bonou', 'Come', 'Cotonou', 'Cove', 'Dangbo', 'Dassa', 'Djougou', 'Dogbo-tota', 'Glazoue', 'Kalale', 'Karimama', 'Kerou', 'Ketou', 'Klouekanme', 'Kobli', 'Malanville', 'Natitingou', 'Ndali', 'Nikki', 'Ouake', 'Ouesse', 'Ouinhi', 'Parakou', 'Pehonko', 'Pobe', 'Porto-novo', 'Sakete', 'Savalou', 'Sinende', 'So-ava', 'Tanguieta', 'Tchaourou', 'Toffo', 'Zangnanado', 'Ze', 'Zogbodome']
    
    liste_marches = ['Abomey', 'Affamè', 'Ahidahomè (Porto-Novo)', 'Azovè', 'Azowlissè', 'Banikoara', 'Bassila', 'Bembèrèkè', 'Bohicon', 'Cobly', 'Comé', 'Covè', 'Dangbo', 'Dantokpa', 'Dassa-Zoumè', 'Dasso', 'Djougou', 'Dogbo', 'Glazoué', 'Hozin', 'Ikpenlè', 'Kalalé', 'Karimama', 'Kassoua-Allah', 'Klouékanmè', 'Kpedekpo', 'Kérou', 'Kétou', 'Malanville (CBM)', "N'Dali", 'Natitingou', 'Nikki', 'Ouando', 'Ouesse', 'Ouègbo', 'Parakou', 'Pobè', 'Péhunco', 'Savalou', 'Sehoue', 'Sinendé', 'So-Ava', 'Sèdjè-Dénou', 'Sékou', 'Tanguiéta', 'Tatonnoukon', 'Tchaourou', 'Yoko', 'Zinvié', 'Zogbodomey', 'Zè']
    
    liste_marchandises = ['Maize', 'Maize (white)', 'Maize (yellow)', 'Rice (Broken, local)', 'Rice (imported)', 'Rice (local)', 'Rice (milled, local)', 'Rice (paddy)']

    col1, col2 = st.columns(2)
    with col1:
        # Sélecteurs de texte : on récupère le nom choisi par l'utilisateur
        dept_nom = st.selectbox("Département", liste_departements)
        ville_nom = st.selectbox("Ville", liste_villes)
        marche_nom = st.selectbox("Marché", liste_marches)
        
        # Conversion transparente en code numérique via la position dans la liste (index)
        departement_code = liste_departements.index(dept_nom)
        ville_code = liste_villes.index(ville_nom)
        marche_code = liste_marches.index(marche_nom)

    with col2:
        march_nom = st.selectbox("Marchandise", liste_marchandises)
        marchandise_code = liste_marchandises.index(march_nom)
        
        # Le mois reste le seul champ numérique à saisir
        mois = st.number_input("Mois de l'année (1 à 12)", min_value=1, max_value=12, step=1)

    # Bouton de prédiction
    st.write("")
    if st.button("Prédire le Prix", type="primary"):
        with st.spinner("Calcul en cours via le backend..."):
            try:
                # Les codes (et non les textes) sont envoyés au backend pour la prédiction
                data = {
                    "Departement": departement_code,
                    "ville": ville_code,
                    "marche": marche_code,
                    "marchandise": marchandise_code,
                    "mois": int(mois),
                    "modele": modele_choisi
                }

                headers = {}
                api_key = get_secret("API_KEY")
                if api_key:
                    headers["X-API-Key"] = api_key

                # Appel API distante (Render) ou locale avec timeout
                response = requests.post(
                    get_predict_url(),
                    json=data,
                    headers=headers,
                    timeout=get_request_timeout(),
                )

                if response.status_code == 200:
                    resultat = response.json()
                    
                    if "error" in resultat:
                        st.error(f"Erreur du modèle : {resultat['error']}")
                    else:
                        prix = resultat["prix_predict"]
                        modele_api = resultat["modele_utilise"]
                        st.success(f"📈 Prix prédit par **{modele_api}** :  {prix:.2f} Francs CFA ")
                elif response.status_code == 401:
                    st.error("Erreur d'authentification auprès de l'API (Clé `API_KEY` invalide ou manquante).")
                elif response.status_code == 422:
                    st.error("Erreur de validation des données envoyées à l'API.")
                elif response.status_code == 503:
                    st.error("Service indisponible : les modèles ne sont pas chargés sur le serveur backend.")
                else:
                    detail = ""
                    try:
                        detail = response.json().get("detail", "")
                    except Exception:
                        detail = response.text
                    st.error(f"Erreur API ({response.status_code}) : {detail or 'Impossible de joindre l API de prédiction.'}")

            except requests.exceptions.Timeout:
                st.error(
                    "⏳ Délai d'attente dépassé (Timeout) lors de la connexion au backend Render. "
                    "Si le serveur était en veille, veuillez réessayer dans quelques secondes."
                )
            except requests.exceptions.ConnectionError:
                st.error(
                    "🔌 Impossible de se connecter au serveur Backend. "
                    "Vérifiez que l'API Render est démarrée et que `BACKEND_URL` est correctement configurée."
                )
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de communication HTTP avec l'API : {e}")
            except Exception as e:
                st.error(f"Erreur inattendue : {e}")

    st.divider()
    if st.button("Déconnexion"):
        st.session_state["authenticated"] = False
        st.rerun()


def main():
    # Configuration de la page
    st.set_page_config(page_title="Prédiction Prix Agricoles", page_icon="🌾", layout="wide")

    st.markdown("""
        <style>
            .stTextInput, .stButton > button {
                border-radius: 10px;
            }
            .main {
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)

    # Exécution de l'application
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        login()
    else:
        predicteur()


if __name__ == "__main__":
    main()
