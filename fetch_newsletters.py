import os.path
import base64
import sqlite3
from datetime import datetime
from email.utils import parsedate_to_datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
DB_FILE = os.path.join('data', 'refined', 'newsletter.db')

def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email (
            id TEXT PRIMARY KEY,
            sender TEXT,
            date_received INTEGER,
            title TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_last_email_timestamp():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(date_received) FROM email")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def save_email_to_db(msg_id, sender, date_received, title):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO email (id, sender, date_received, title)
            VALUES (?, ?, ?, ?)
        ''', (msg_id, sender, date_received, title))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Déjà en base
    conn.close()

def is_email_already_fetched(msg_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM email WHERE id = ?", (msg_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_header(headers, name):
    for h in headers:
        if h['name'].lower() == name.lower():
            return h['value']
    return ""

def get_email_body(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/html':
                data = part['body'].get('data')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        # Fallback to plain text
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
    else:
        data = payload['body'].get('data')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
    return ""

def run():
    print("Initialisation de la base de données (table email)...")
    init_db()
    
    print("Connexion à l'API Gmail...")
    service = authenticate_gmail()
    
    last_timestamp = get_last_email_timestamp()
    
    query = "from:dan@tldrnewsletter.com OR from:tldr@tldrnewsletter.com"
    if last_timestamp:
        # On ajoute 1 seconde pour éviter de récupérer le même email
        query += f" after:{last_timestamp + 1}"
        
    print(f"Recherche des emails avec la requête : {query}")
    
    try:
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("Aucun nouveau message trouvé.")
            return
            
        print(f"\n[OK] {len(messages)} nouveaux messages trouvés :\n")
        
        output_dir = os.path.join('data', 'raw', 'newsletter', 'tldr-ai')
        os.makedirs(output_dir, exist_ok=True)
        
        new_messages_count = 0
        for i, message in enumerate(messages, 1):
            msg_id = message['id']
            
            # Vérifier si on a déjà traité cet email avant de télécharger le corps complet
            if is_email_already_fetched(msg_id):
                continue
                
            new_messages_count += 1
            msg_details = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            payload = msg_details['payload']
            headers = payload['headers']
            subject = get_header(headers, 'Subject')
            date_str = get_header(headers, 'Date')
            sender = get_header(headers, 'From')
            
            try:
                date_obj = parsedate_to_datetime(date_str)
                timestamp = int(date_obj.timestamp())
                file_date = date_obj.strftime("%Y%m%d")
            except:
                timestamp = int(datetime.now().timestamp())
                file_date = "YYYYMMDD"
                
            body = get_email_body(payload)
            filename = f"{file_date}_tldr-ai_{msg_id}.html"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"<!-- Subject: {subject} -->\n")
                f.write(f"<!-- Date: {date_str} -->\n")
                f.write(f"<!-- ID: {msg_id} -->\n")
                f.write(body)
                
            save_email_to_db(msg_id, sender, timestamp, subject)
            print(f" -> Email téléchargé et sauvegardé : {filename} ({subject})")
            
        if new_messages_count == 0:
            print("Aucun nouveau message (les messages trouvés étaient déjà en base).")
        else:
            print(f"[OK] {new_messages_count} emails traités.")
            
    except Exception as e:
        print(f"Erreur lors de la récupération : {e}")

if __name__ == '__main__':
    run()
