"""
Point d'entrée racine pour Streamlit Community Cloud.
Permet de cibler directement `frontend.py` à la racine du dépôt GitHub
ou `app/frontend.py`.
"""
from app.frontend import main

if __name__ == "__main__":
    main()
