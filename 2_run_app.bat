@echo off
echo ===================================================
echo Initialisation et Lancement du Projet
echo ===================================================

:: Activation de l'environnement
IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo [ERREUR] L'environnement virtuel est introuvable. Executez d'abord 1_setup_env.bat.
    pause
    exit /b 1
)
call .venv\Scripts\activate

:: Installation des requirements
echo Installation et verification des dependances...
pip install -r requirements.txt

:: Lancement du Backend (FastAPI) dans une nouvelle fenetre
echo Lancement de l'API (Backend)...
start "Backend - FastAPI" cmd /k "call .venv\Scripts\activate && uvicorn app.Fast_api_price:app --host 127.0.0.1 --port 8000 --reload"

:: Lancement du Frontend (Streamlit) dans une nouvelle fenetre
echo Lancement de l'Interface (Frontend)...
start "Frontend - Streamlit" cmd /k "call .venv\Scripts\activate && streamlit run app/frontend.py"

echo.
echo L'application est en cours d'execution dans les nouvelles fenetres.
echo Vous pouvez fermer cette fenetre principale.
pause
