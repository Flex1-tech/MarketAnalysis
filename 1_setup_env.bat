@echo off
echo ===================================================
echo Creation de l'environnement virtuel (.venv)
echo ===================================================

:: Tente de creer l'environnement avec Python 3.11 ou 3.12 ou python par defaut
py -3.11 -m venv .venv 2>nul
IF %ERRORLEVEL% NEQ 0 (
    py -3.12 -m venv .venv 2>nul
)
IF %ERRORLEVEL% NEQ 0 (
    python -m venv .venv
)

IF %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
    echo Veuillez telecharger et installer Python 3.11 ou 3.12 depuis python.org.
    pause
    exit /b 1
)

echo Environnement virtuel ".venv" cree avec succes !
pause
