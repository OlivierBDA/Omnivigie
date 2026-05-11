import os
import glob
import sqlite3
import urllib.parse
import re
from bs4 import BeautifulSoup

DB_DIR = os.path.join('data', 'refined')
DB_FILE = os.path.join(DB_DIR, 'newsletter.db')
RAW_DIR = os.path.join('data', 'raw', 'newsletter', 'tldr-ai')

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tldr_ai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            newsletter_date TEXT,
            section TEXT,
            title TEXT,
            url TEXT UNIQUE,
            reading_time TEXT,
            summary TEXT,
            is_sponsor BOOLEAN
        )
    ''')
    conn.commit()
    conn.close()

def clean_tldr_url(tracking_url):
    """Extrait l'URL réelle du lien de tracking."""
    if not tracking_url:
        return ""
    parts = tracking_url.split('/')
    for part in parts:
        # Les URLs encodées commencent souvent par http:%2F%2F ou https:%2F%2F
        if part.startswith('http:%2F%2F') or part.startswith('https:%2F%2F'):
            return urllib.parse.unquote(part)
    return tracking_url

def parse_html_file(filepath):
    print(f"Parsing du fichier : {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    # Extraire la date depuis le nom du fichier (YYYYMMDD)
    basename = os.path.basename(filepath)
    date_match = re.match(r'^(\d{8})_', basename)
    newsletter_date = date_match.group(1) if date_match else "Inconnue"
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    current_section = "Intro"
    articles = []
    
    # Parcourir tous les blocs de texte
    for text_block in soup.find_all('div', class_='text-block'):
        # 1. Détecter un changement de section
        h1 = text_block.find('h1')
        if h1 and h1.find('strong'):
            current_section = h1.text.strip()
            continue
            
        # 2. Chercher un article (qui contient un lien <a>)
        a_tag = text_block.find('a')
        if not a_tag:
            continue
            
        # Le titre est généralement en gras (<strong>) dans le lien
        strong = a_tag.find('strong')
        if not strong:
            continue
            
        title_full = strong.text.strip()
        url_tracking = a_tag.get('href')
        url_clean = clean_tldr_url(url_tracking)
        
        # Ignorer les liens internes ou vers la newsletter elle-même si ce ne sont pas de vrais articles
        if "tldrnewsletter.com/actions" in url_clean:
            continue
            
        # 3. Extraction du temps de lecture et du titre
        time_match = re.search(r'\(([^)]+read)\)$', title_full)
        if time_match:
            reading_time = time_match.group(1)
            title = title_full[:time_match.start()].strip()
        else:
            reading_time = ""
            title = title_full
            
        # 4. Identification du sponsor
        is_sponsor = False
        if "(Sponsor)" in title or "(sponsor)" in title.lower():
            is_sponsor = True
            # Nettoyer le titre
            title = re.sub(r'\s*\(Sponsor\)', '', title, flags=re.IGNORECASE).strip()
            
        # 5. Extraction du résumé
        summary = ""
        # Souvent dans le <span> qui suit avec une police spécifique
        spans = text_block.find_all('span', recursive=True)
        for span in spans:
            style = span.get('style', '')
            if style and 'font-family' in style.lower():
                # On s'assure qu'on ne prend pas juste le span du titre
                text = span.text.strip()
                if text and text != title_full:
                    summary = text
                    break
                    
        # Fallback pour le résumé
        if not summary:
            summary = text_block.text.replace(title_full, "").strip()
            
        articles.append({
            'newsletter_date': newsletter_date,
            'section': current_section,
            'title': title,
            'url': url_clean,
            'reading_time': reading_time,
            'summary': summary,
            'is_sponsor': is_sponsor
        })
        
    return articles

def save_articles(articles):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    inserted = 0
    for art in articles:
        try:
            cursor.execute('''
                INSERT INTO tldr_ai (newsletter_date, section, title, url, reading_time, summary, is_sponsor)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                art['newsletter_date'], 
                art['section'], 
                art['title'], 
                art['url'], 
                art['reading_time'], 
                art['summary'], 
                art['is_sponsor']
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # L'URL existe déjà (doublon)
            pass
            
    conn.commit()
    conn.close()
    return inserted

def main():
    print("Initialisation de la base de données...")
    init_db()
    
    if not os.path.exists(RAW_DIR):
        print(f"Le dossier {RAW_DIR} n'existe pas.")
        return
        
    html_files = glob.glob(os.path.join(RAW_DIR, '*.html'))
    if not html_files:
        print("Aucun fichier HTML trouvé à parser.")
        return
        
    total_inserted = 0
    for filepath in html_files:
        articles = parse_html_file(filepath)
        print(f" -> {len(articles)} articles potentiels trouvés dans l'email.")
        
        inserted = save_articles(articles)
        total_inserted += inserted
        print(f" -> {inserted} nouveaux articles sauvegardés en base de données.")
    print(f"\n[OK] Opération terminée. Total de nouveaux articles en base : {total_inserted}")

if __name__ == '__main__':
    main()
