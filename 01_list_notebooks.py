import asyncio
import os
from dotenv import load_dotenv
from notebooklm import NotebookLMClient

# Charge les variables d'environnement depuis le fichier .env (si présent)
load_dotenv()

async def main():
    print("Initialisation du client NotebookLM...")
    
    # La méthode from_storage() lit l'authentification sauvegardée.
    # Soit via le dossier ~/.notebooklm/ généré par 'notebooklm login'
    # Soit via la variable d'environnement NOTEBOOKLM_AUTH_JSON
    try:
        async with await NotebookLMClient.from_storage() as client:
            print("Connexion réussie. Récupération des carnets (notebooks)...")
            
            # Récupération de la liste des notebooks
            notebooks = await client.notebooks.list()
            
            print(f"\n--- Vous avez {len(notebooks)} carnets dans votre espace NotebookLM ---")
            for nb in notebooks:
                print(f"ID : {nb.id}")
                print(f"Titre : {nb.title}")
                print(f"Date de création : {getattr(nb, 'created_at', 'Non spécifiée')}")
                print("-" * 40)
                
    except Exception as e:
        print(f"\nErreur de connexion : {e}")
        print("\nNote : Avez-vous bien configuré l'authentification ?")
        print("Pour vous authentifier facilement, exécutez la commande : notebooklm login")

if __name__ == "__main__":
    asyncio.run(main())
