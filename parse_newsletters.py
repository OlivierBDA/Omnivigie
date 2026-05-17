import os
import glob
import sqlite3
import urllib.parse
import re
import shutil
from bs4 import BeautifulSoup

DB_DIR = os.path.join('data', 'refined')
DB_FILE = os.path.join(DB_DIR, 'newsletter.db')
RAW_DIR = os.path.join('data', 'raw', 'newsletter', 'tldr-ai')
PROCESSED_DIR = os.path.join(RAW_DIR, 'processed')

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
    
    # Ajout de email_id si non existant
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(tldr_ai)").fetchall()]
    if 'email_id' not in columns:
        cursor.execute("ALTER TABLE tldr_ai ADD COLUMN email_id TEXT")
        
    conn.commit()
    conn.close()

def clean_tldr_url(tracking_url):
    if not tracking_url:
        return ""
    parts = tracking_url.split('/')
    for part in parts:
        if part.startswith('http:%2F%2F') or part.startswith('https:%2F%2F'):
            return urllib.parse.unquote(part)
    return tracking_url

def parse_html_file(filepath):
    print(f"Parsing du fichier : {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    basename = os.path.basename(filepath)
    date_match = re.match(r'^(\d{8})_', basename)
    newsletter_date = date_match.group(1) if date_match else "Inconnue"
    
    # Extraire l'ID du message
    email_id = None
    id_match = re.search(r'<!-- ID: (.*?) -->', html_content)
    if id_match:
        email_id = id_match.group(1).strip()
    else:
        # Fallback sur le nom de fichier
        file_id_match = re.search(r'_([^_]+)\.html$', basename)
        if file_id_match:
            email_id = file_id_match.group(1)
            
    soup = BeautifulSoup(html_content, 'html.parser')
    
    current_section = "Intro"
    articles = []
    
    for text_block in soup.find_all('div', class_='text-block'):
        h1 = text_block.find('h1')
        if h1 and h1.find('strong'):
            current_section = h1.text.strip()
            continue
            
        a_tag = text_block.find('a')
        if not a_tag:
            continue
            
        strong = a_tag.find('strong')
        if not strong:
            continue
            
        title_full = strong.text.strip()
        url_tracking = a_tag.get('href')
        url_clean = clean_tldr_url(url_tracking)
        
        if "tldrnewsletter.com/actions" in url_clean:
            continue
            
        time_match = re.search(r'\(([^)]+read)\)$', title_full)
        if time_match:
            reading_time = time_match.group(1)
            title = title_full[:time_match.start()].strip()
        else:
            reading_time = ""
            title = title_full
            
        is_sponsor = False
        if "(Sponsor)" in title or "(sponsor)" in title.lower():
            is_sponsor = True
            title = re.sub(r'\s*\(Sponsor\)', '', title, flags=re.IGNORECASE).strip()
            
        summary = ""
        spans = text_block.find_all('span', recursive=True)
        for span in spans:
            style = span.get('style', '')
            if style and 'font-family' in style.lower():
                text = span.text.strip()
                if text and text != title_full:
                    summary = text
                    break
                    
        if not summary:
            summary = text_block.text.replace(title_full, "").strip()
            
        articles.append({
            'newsletter_date': newsletter_date,
            'email_id': email_id,
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
                INSERT INTO tldr_ai (newsletter_date, section, title, url, reading_time, summary, is_sponsor, email_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                art['newsletter_date'], 
                art['section'], 
                art['title'], 
                art['url'], 
                art['reading_time'], 
                art['summary'], 
                art['is_sponsor'],
                art['email_id']
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
            
    conn.commit()
    conn.close()
    return inserted

def run():
    print("Initialisation de la base de données...")
    init_db()
    
    if not os.path.exists(RAW_DIR):
        print(f"Le dossier {RAW_DIR} n'existe pas.")
        return
        
    os.makedirs(PROCESSED_DIR, exist_ok=True)
        
    html_files = [f for f in glob.glob(os.path.join(RAW_DIR, '*.html')) if os.path.isfile(f)]
    if not html_files:
        print("Aucun fichier HTML non traité trouvé.")
        return
        
    total_inserted = 0
    for filepath in html_files:
        articles = parse_html_file(filepath)
        print(f" -> {len(articles)} articles potentiels trouvés dans l'email.")
        
        inserted = save_articles(articles)
        total_inserted += inserted
        print(f" -> {inserted} nouveaux articles sauvegardés en base de données.")
        
        # Déplacer le fichier
        filename = os.path.basename(filepath)
        dest_path = os.path.join(PROCESSED_DIR, filename)
        shutil.move(filepath, dest_path)
        print(f" -> Fichier déplacé vers {PROCESSED_DIR}")
        
    print(f"\n[OK] Opération de parsing terminée. Total de nouveaux articles en base : {total_inserted}")

if __name__ == '__main__':
    run()
