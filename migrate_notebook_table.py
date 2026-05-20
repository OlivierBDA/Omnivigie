import sqlite3
import os

DB_FILE = os.path.join('data', 'refined', 'newsletter.db')

def migrate():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Création de la table notebook
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notebook (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            created_at DATETIME,
            mindmap_json TEXT
        )
    ''')
    
    # 2. Ajout de notebook_id à tldr_ai
    # Vérification si la colonne existe déjà
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(tldr_ai)").fetchall()]
    if 'notebook_id' not in columns:
        cursor.execute("ALTER TABLE tldr_ai ADD COLUMN notebook_id INTEGER")
        print("Colonne 'notebook_id' ajoutée à la table 'tldr_ai'.")
    else:
        print("La colonne 'notebook_id' existe déjà dans 'tldr_ai'.")
        
    conn.commit()
    conn.close()
    print("Migration terminée avec succès.")

if __name__ == "__main__":
    migrate()
