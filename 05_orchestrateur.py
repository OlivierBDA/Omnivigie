import os
import sys
import json
import time
import asyncio
import datetime
from dotenv import load_dotenv

from src.database import init_db, save_article
from src.search_engine import fetch_articles
from src.notebook_manager import setup_notebook, generate_podcast

from notebooklm.client import NotebookLMClient

CONFIG_FILE = 'config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Fichier {CONFIG_FILE} introuvable.")
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def wait_with_progress(duration_seconds, interval_seconds=30):
    """Met en pause le programme avec un affichage régulier pour rassurer l'utilisateur."""
    print(f"\n[ATTENTE] Début d'une pause de {duration_seconds // 60} minutes pour laisser le temps d'ingestion à NotebookLM...")
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed >= duration_seconds:
            break
        remaining = duration_seconds - elapsed
        print(f"  -> {datetime.datetime.now().strftime('%H:%M:%S')} : En attente... (Reste environ {int(remaining)} secondes)")
        time.sleep(min(interval_seconds, remaining))
    print("[ATTENTE] Terminé.\n")

async def process_theme(theme, client):
    theme_id = theme.get("id")
    theme_name = theme.get("name")
    query = theme.get("query")
    counter = theme.get("counter", 1)
    
    print(f"\n{'='*50}")
    print(f"Traitement du thème : {theme_name} (Veille n°{counter:02d})")
    print(f"{'='*50}")
    
    # 1. Recherche Tavily
    articles = fetch_articles(query, max_results=5, days=15)
    if not articles:
        print("Aucun article récent trouvé.")
        return False
        
    # 2. Enregistrement en base de données et Dédoublonnage
    print("\nSauvegarde dans SQLite et filtrage des doublons...")
    new_urls = []
    for article in articles:
        title = article.get("title", "Sans titre")
        url = article.get("url")
        score = article.get("score", 0)
        published_date = article.get("published_date", "")
        
        if not url:
            continue
            
        inserted = save_article(theme_id, title, url, score, published_date)
        if inserted:
            print(f" [NOUVEAU] {title[:60]}...")
            new_urls.append(url)
        else:
            print(f" [DOUBLON] L'article a déjà été traité précédemment.")
            
    if not new_urls:
        print("\nTous les articles trouvés sont des doublons. Rien de nouveau à analyser.")
        return False
        
    # 3. NotebookLM : Création et ajout des sources
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    notebook_title = f"[AI] {date_str} {counter:02d} {theme_name}"
    
    print("\n--- Intégration NotebookLM ---")
    notebook_id = await setup_notebook(client, notebook_title, new_urls)
    
    # 4. Attente (pour le traitement Google)
    wait_with_progress(300, interval_seconds=30)
    
    # 5. Génération Audio
    await generate_podcast(client, notebook_id)
    
    # Mise à jour du compteur pour la prochaine fois
    theme["counter"] = counter + 1
    return True

async def main():
    load_dotenv()
    
    print("Initialisation de la base de données...")
    init_db()
    
    print("Chargement de la configuration...")
    config = load_config()
    
    # Connexion globale NotebookLM (pour ne pas rouvrir le navigateur à chaque thème si on en a plusieurs)
    try:
        async with await NotebookLMClient.from_storage() as client:
            for theme in config:
                success = await process_theme(theme, client)
                if success:
                    save_config(config)
                    
    except Exception as e:
        print(f"\nErreur globale de l'orchestrateur : {e}")

if __name__ == "__main__":
    asyncio.run(main())
