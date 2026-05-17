import os
import asyncio

# Import des modules
import fetch_newsletters
import parse_newsletters
import qualify_articles
import create_themed_notebook
import generate_podcast

import sys

def print_banner(title):
    print("\n" + "="*50)
    print(f" {title} ".center(50, "="))
    print("="*50 + "\n")

async def auto_login_notebooklm():
    print_banner("ÉTAPE 0 : AUTHENTIFICATION NOTEBOOKLM")
    print("Lancement de la commande 'notebook login'...")
    
    # Lancement du processus en arrière-plan avec l'exécutable Python courant
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "notebooklm", "login",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    wait_time = 30
    print(f"Le navigateur va s'ouvrir. Attente de {wait_time} secondes pour l'auto-connexion...")
    for i in range(wait_time, 0, -5):
        print(f"... {i} secondes restantes")
        await asyncio.sleep(5)
        
    print("Envoi de la validation (touche Entrée) pour capturer la session...")
    
    if process.stdin:
        process.stdin.write(b'\n')
        await process.stdin.drain()
        
    # Attendre la fin de la commande
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0:
        print("[OK] Authentification NotebookLM mise à jour avec succès !")
    else:
        print(f"[AVERTISSEMENT] L'authentification a retourné un code d'erreur ({process.returncode}).")
        if stderr:
            print(stderr.decode(errors='replace'))

async def main():
    try:
        # 0. Auto-Login
        await auto_login_notebooklm()
        
        # 1. Fetch
        print_banner("ÉTAPE 1 : RÉCUPÉRATION DES EMAILS")
        fetch_newsletters.run()
        
        # 2. Parse
        print_banner("ÉTAPE 2 : EXTRACTION DES ARTICLES")
        parse_newsletters.run()
        
        # 3. Qualify
        print_banner("ÉTAPE 3 : QUALIFICATION PAR L'IA")
        qualify_articles.run()
        
        # 4. Create Notebook
        print_banner("ÉTAPE 4 : CRÉATION DU CARNET")
        print("L'analyse est terminée. Voici les thèmes disponibles pour créer un carnet :")
        notebook_name = await create_themed_notebook.run()
        
        if not notebook_name:
            print("\nAucun carnet créé. Fin du programme.")
            return
            
        # 5. Generate Podcast
        print_banner("ÉTAPE 5 : GÉNÉRATION DU PODCAST")
        confirm = input(f"Voulez-vous lancer la génération du podcast long pour le carnet '{notebook_name}' ? (y/n) : ")
        if confirm.lower() == 'y':
            await generate_podcast.run(notebook_name)
        else:
            print("Génération audio annulée. Vous pourrez le faire plus tard manuellement.")
            
        print("\n[SUCCES] Pipeline Omnivigie terminé avec succès !")
        
    except Exception as e:
        print(f"\n[ERREUR CRITIQUE] Une erreur est survenue dans l'orchestrateur : {e}")

if __name__ == '__main__':
    asyncio.run(main())
