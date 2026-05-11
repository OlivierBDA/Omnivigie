import sqlite3
import datetime

DB_FILE = 'omnivigie.db'

def init_db():
    """Initialise la base de données et crée la table articles si nécessaire."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme_id TEXT,
            title TEXT,
            url TEXT UNIQUE,
            score REAL,
            published_date TEXT,
            fetch_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_article(theme_id, title, url, score, published_date):
    """
    Sauvegarde un article dans la base de données.
    Si l'URL existe déjà, l'article n'est pas ajouté (dédoublonnage).
    Retourne True si inséré, False si c'est un doublon ou en cas d'erreur.
    """
    fetch_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # On vérifie d'abord si l'URL existe pour pouvoir retourner le statut
    cursor.execute('SELECT id FROM articles WHERE url = ?', (url,))
    if cursor.fetchone():
        conn.close()
        return False
        
    try:
        cursor.execute('''
            INSERT INTO articles (theme_id, title, url, score, published_date, fetch_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (theme_id, title, url, score, published_date, fetch_date))
        conn.commit()
        inserted = True
    except sqlite3.IntegrityError:
        # Sécurité supplémentaire au cas où (UNIQUE constraint failed)
        inserted = False
    finally:
        conn.close()
        
    return inserted
