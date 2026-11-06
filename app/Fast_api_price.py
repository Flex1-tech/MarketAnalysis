import hmac
import logging
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import joblib
import pandas as pd
from pydantic import BaseModel, Field
import uvicorn
import xgboost as xgb

# Configuration du logger
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fast_api_price")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


def load_env_file(env_path: Path) -> None:
    """Charge un fichier .env sans dépendance externe s'il existe."""
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

MODEL_DIR = Path(os.getenv("MODEL_DIR", str(BASE_DIR / "model")))
RF_MODEL_PATH = Path(os.getenv("RF_MODEL_PATH", str(MODEL_DIR / "RANDOM_FOREST.pkl")))
XGB_MODEL_PATH = Path(os.getenv("XGB_MODEL_PATH", str(MODEL_DIR / "XGBOST.pkl")))

app = FastAPI(
    title="API de Prédiction des Prix Agricoles",
    description="API REST déployée sur Render pour l'estimation des prix agricoles au Bénin",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Chargement global des deux modèles avec pathlib (compatible Windows & Linux)
try:
    model_rf = joblib.load(RF_MODEL_PATH)
    model_xgb = joblib.load(XGB_MODEL_PATH)
    logger.info("Modèles chargés avec succès depuis %s", MODEL_DIR)
except Exception as e:
    logger.error("Erreur lors du chargement des modèles : %s", e)
    model_rf, model_xgb = None, None


class PredictionRequest(BaseModel):
    Departement: int = Field(..., ge=0, le=11, description="Code numérique du département (0 à 11)")
    ville: int = Field(..., ge=0, le=45, description="Code numérique de la ville (0 à 45)")
    marche: int = Field(..., ge=0, le=50, description="Code numérique du marché (0 à 50)")
    marchandise: int = Field(..., ge=0, le=7, description="Code numérique de la marchandise (0 à 7)")
    mois: int = Field(..., ge=1, le=12, description="Mois de l'année (1 à 12)")
    modele: Literal["Random Forest", "XGBoost"] = Field(
        default="Random Forest",
        description="Algorithme de prédiction choisi",
    )


class PredictionResponse(BaseModel):
    prix_predict: float
    modele_utilise: str


def verify_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    """Protège l'endpoint /predict par clé API (en-tête X-API-Key)."""
    expected_key = os.getenv("API_KEY", "").strip()
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration serveur incomplète : variable API_KEY non définie.",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé d'API invalide ou manquante.",
        )


@app.get("/")
def greet():
    return {"message": "API de Prédiction des Prix Agricoles active"}


@app.get("/health")
def health_check():
    rf_loaded = model_rf is not None
    xgb_loaded = model_xgb is not None
    if not (rf_loaded and xgb_loaded):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "models_loaded": {
                    "random_forest": rf_loaded,
                    "xgboost": xgb_loaded,
                },
            },
        )
    return {
        "status": "healthy",
        "models_loaded": {
            "random_forest": rf_loaded,
            "xgboost": xgb_loaded,
        },
    }


@app.post("/predict", response_model=PredictionResponse, dependencies=[Depends(verify_api_key)])
async def predict(payload: PredictionRequest):
    if model_rf is None or model_xgb is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Les modèles ne sont pas chargés correctement côté serveur.",
        )

    # 1. Création d'un DataFrame avec les colonnes dans l'ordre EXACT attendu par les modèles
    input_data = pd.DataFrame(
        [[
            payload.Departement,
            payload.ville,
            payload.marche,
            payload.marchandise,
            payload.mois,
        ]],
        columns=["Departement", "ville", "marche", "marchandise", "mois"],
    )

    modele_choisi = payload.modele

    try:
        # 2. Prédiction adaptative selon le modèle choisi
        if modele_choisi == "XGBoost":
            # XGBoost a besoin d'être converti en DMatrix
            dmatrix_data = xgb.DMatrix(input_data)
            prediction = float(model_xgb.predict(dmatrix_data)[0])
        else:
            # Random Forest traite le DataFrame directement
            prediction = float(model_rf.predict(input_data)[0])

        return {
            "prix_predict": prediction,
            "modele_utilise": modele_choisi,
        }

    except Exception as e:
        logger.exception("Erreur lors de la prédiction : %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors du calcul de la prédiction.",
        ) from e


if __name__ == "__main__":
    # Support direct du port dynamique PORT injecté par Render
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.Fast_api_price:app", host="0.0.0.0", port=port)
