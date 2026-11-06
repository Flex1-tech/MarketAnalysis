import hashlib
import os
from pathlib import Path
import socket
import threading
import time
import unittest
from unittest.mock import patch

from fastapi import HTTPException
import requests
import uvicorn

# Configuration de l'environnement de test avant import
TEST_PASSWORD = "TestSecurePassword2026!"
TEST_PASSWORD_HASH = hashlib.sha256(TEST_PASSWORD.encode("utf-8")).hexdigest()
os.environ["API_KEY"] = "test-api-key-secret"
os.environ["ADMIN_USER"] = "admin"
os.environ["ADMIN_PASSWORD_HASH"] = TEST_PASSWORD_HASH
os.environ["BACKEND_TIMEOUT"] = "15"

import app.Fast_api_price as backend_module  # noqa: E402
import app.frontend as frontend_module  # noqa: E402
from app.frontend import (  # noqa: E402
    get_predict_url,
    get_request_timeout,
    get_secret,
    verify_credentials,
)


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestStreamlitCloudAndRenderArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = get_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        os.environ["PORT"] = str(cls.port)
        os.environ["BACKEND_URL"] = cls.base_url
        cls.headers = {"X-API-Key": "test-api-key-secret"}

        config = uvicorn.Config(
            backend_module.app,
            host="127.0.0.1",
            port=cls.port,
            log_level="warning",
        )
        cls.server = uvicorn.Server(config)
        cls.server_thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.server_thread.start()

        # Attendre que le serveur Uvicorn soit prêt
        for _ in range(50):
            try:
                r = requests.get(f"{cls.base_url}/health", timeout=1)
                if r.status_code == 200:
                    break
            except requests.RequestException:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.server_thread.join(timeout=5)

    def test_01_models_loaded_with_pathlib(self):
        """1. Vérifier le chargement des deux modèles sur le Backend."""
        self.assertIsNotNone(backend_module.model_rf, "Le modèle Random Forest doit être chargé.")
        self.assertIsNotNone(backend_module.model_xgb, "Le modèle XGBoost doit être chargé.")
        self.assertIsInstance(backend_module.RF_MODEL_PATH, Path)
        self.assertIsInstance(backend_module.XGB_MODEL_PATH, Path)
        self.assertTrue(backend_module.RF_MODEL_PATH.is_file())
        self.assertTrue(backend_module.XGB_MODEL_PATH.is_file())

    def test_02_health_endpoint(self):
        """2. Vérifier /health (200 OK et 503 si modèle manquant)."""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "healthy")
        self.assertTrue(body["models_loaded"]["random_forest"])
        self.assertTrue(body["models_loaded"]["xgboost"])

        with patch.object(backend_module, "model_rf", None):
            with self.assertRaises(HTTPException) as ctx:
                backend_module.health_check()
            self.assertEqual(ctx.exception.status_code, 503)

    def test_03_predict_random_forest_and_xgboost(self):
        """3. Tester les prédictions Random Forest et XGBoost via HTTP."""
        for model_name, expected_price in [
            ("Random Forest", 168.082112),
            ("XGBoost", 118.02826),
        ]:
            payload = {
                "Departement": 0,
                "ville": 0,
                "marche": 0,
                "marchandise": 0,
                "mois": 1,
                "modele": model_name,
            }
            response = requests.post(
                get_predict_url(),
                json=payload,
                headers={"X-API-Key": get_secret("API_KEY")},
                timeout=get_request_timeout(),
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["modele_utilise"], model_name)
            self.assertAlmostEqual(data["prix_predict"], expected_price, places=3)

    def test_04_pydantic_validation_and_api_key_protection(self):
        """4. Tester la validation des données (422) et la protection par clé API (401)."""
        # Mois invalide (> 12)
        res_month = requests.post(
            get_predict_url(),
            json={"Departement": 0, "ville": 0, "marche": 0, "marchandise": 0, "mois": 13, "modele": "Random Forest"},
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(res_month.status_code, 422)

        # Département hors bornes (> 11)
        res_dept = requests.post(
            get_predict_url(),
            json={"Departement": 99, "ville": 0, "marche": 0, "marchandise": 0, "mois": 6, "modele": "Random Forest"},
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(res_dept.status_code, 422)

        # Sans clé API -> 401
        res_no_key = requests.post(
            get_predict_url(),
            json={"Departement": 0, "ville": 0, "marche": 0, "marchandise": 0, "mois": 6, "modele": "Random Forest"},
            timeout=5,
        )
        self.assertEqual(res_no_key.status_code, 401)

        # Avec mauvaise clé API -> 401
        res_bad_key = requests.post(
            get_predict_url(),
            json={"Departement": 0, "ville": 0, "marche": 0, "marchandise": 0, "mois": 6, "modele": "Random Forest"},
            headers={"X-API-Key": "invalid-key"},
            timeout=5,
        )
        self.assertEqual(res_bad_key.status_code, 401)

    def test_05_streamlit_secrets_integration_and_auth(self):
        """5. Tester la récupération via st.secrets (Streamlit Cloud) et l'authentification."""
        cloud_pass = "CloudSecretPass2026!"
        cloud_hash = hashlib.sha256(cloud_pass.encode("utf-8")).hexdigest()
        mock_secrets = {
            "BACKEND_URL": "https://agri-price-backend.onrender.com/",
            "API_KEY": "render-prod-api-key",
            "ADMIN_USER": "cloud_admin",
            "ADMIN_PASSWORD_HASH": cloud_hash,
        }
        with patch.object(frontend_module.st, "secrets", mock_secrets):
            self.assertEqual(get_predict_url(), "https://agri-price-backend.onrender.com/predict")
            self.assertEqual(get_secret("API_KEY"), "render-prod-api-key")
            self.assertTrue(verify_credentials("cloud_admin", cloud_pass))
            self.assertFalse(verify_credentials("cloud_admin", "1234"))
            self.assertFalse(verify_credentials("admin", cloud_pass))


if __name__ == "__main__":
    unittest.main(verbosity=2)
