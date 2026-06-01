import os
import asyncio
import sqlite3
from datetime import datetime
from collections import defaultdict
import json
from notebooklm.client import NotebookLMClient

DB_FILE = os.path.join('data', 'refined', 'newsletter.db')
THEMES_FILE = 'themes.json'

def load_themes():
    with open(THEMES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_pending_articles():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # On récupère les articles intéressants qui n'ont pas encore été traités
    cursor.execute("SELECT id, title, url, tags FROM tldr_ai WHERE is_interesting = 1 AND is_processed = 0")
    articles = cursor.fetchall()
    conn.close()
    return articles

def group_by_theme(articles):
    theme_map = defaultdict(list)
    for art_id, title, url, tags in articles:
        if not tags:
            continue
        # Les tags sont séparés par des virgules
        for tag in tags.split(','):
            tag = tag.strip()
            if tag:
                theme_map[tag].append((art_id, title, url))
    return theme_map

def insert_notebook(notebook_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notebook (name, created_at) VALUES (?, datetime('now'))", (notebook_name,))
    notebook_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return notebook_id

def mark_articles_as_processed(article_ids, notebook_id, notebook_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for art_id in article_ids:
        cursor.execute("UPDATE tldr_ai SET is_processed = 1, notebook_id = ?, notebook_name = ? WHERE id = ?", (notebook_id, notebook_name, art_id))
    conn.commit()
    conn.close()

async def run():
    print("Recherche des articles en attente...")
    articles = get_pending_articles()
    
    if not articles:
        print("Aucun article pertinent en attente de traitement.")
        return None
        
    theme_map = group_by_theme(articles)
    
    print("\nThèmes disponibles :")
    themes_list = load_themes()
    for i, theme in enumerate(themes_list, 1):
        count = len(theme_map.get(theme, []))
        print(f"[{i}] {theme} ({count} articles)")
        
    print("[0] Quitter")
    
    choice = input("\nEntrez le numéro du thème à regrouper dans un carnet : ")
    try:
        choice_idx = int(choice)
        if choice_idx == 0:
            return None
        if choice_idx < 1 or choice_idx > len(themes_list):
            print("Choix invalide.")
            return None
    except ValueError:
        print("Veuillez entrer un nombre valide.")
        return None
        
    selected_theme = themes_list[choice_idx - 1]
    selected_articles = theme_map.get(selected_theme, [])
    
    if not selected_articles:
        print(f"\nIl n'y a actuellement aucun article en attente pour le thème '{selected_theme}'.")
        print("Veuillez choisir un autre thème ou attendre de nouvelles newsletters.")
        return None
        
    print(f"\nVous avez sélectionné '{selected_theme}'.")
    for _, title, _ in selected_articles:
        print(f" - {title}")
        
    confirm = input("\nVoulez-vous créer le carnet NotebookLM pour ces articles ? (y/n) : ")
    if confirm.lower() != 'y':
        print("Annulation.")
        return None
        
    return await create_notebook_from_articles(selected_theme, selected_articles)

async def create_notebook_from_articles(selected_theme, selected_articles):
    current_time = datetime.now().strftime('%Y-%m-%d')
    notebook_name = f"[AI] {current_time} TLDR-{selected_theme}"
    
    print(f"\nConnexion à NotebookLM pour la création du carnet '{notebook_name}'...")
    
    try:
        async with await NotebookLMClient.from_storage() as client:
            nb = await client.notebooks.create(notebook_name)
            print(f"Carnet créé avec succès (ID: {nb.id}) !")
            
            article_ids = []
            for i, (art_id, title, url) in enumerate(selected_articles, 1):
                print(f"[{i}/{len(selected_articles)}] Ajout de : {title}")
                try:
                    await client.sources.add_url(nb.id, url)
                    article_ids.append(art_id)
                except Exception as e:
                    print(f" -> Erreur lors de l'ajout de {url} : {e}")
                    
            print("\nMise à jour de la base de données...")
            notebook_id = insert_notebook(notebook_name)
            mark_articles_as_processed(article_ids, notebook_id, notebook_name)
            print("Base de données mise à jour avec succès.")
            
            print(f"\n[OK] Le carnet '{notebook_name}' est prêt dans NotebookLM.")
            return notebook_name
            
    except Exception as e:
        print(f"Erreur avec NotebookLM : {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run())
