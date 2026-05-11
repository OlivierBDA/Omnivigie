import os.path
import base64
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Autorisation de lecture seule sur Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """Gère l'authentification OAuth 2.0 avec l'API Gmail."""
    creds = None
    
    # Le fichier token.json stocke le token d'accès (et de rafraîchissement) 
    # de l'utilisateur, et est créé automatiquement après la 1ère connexion réussie.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # Si on n'a pas de credentials valides, on demande à l'utilisateur de se connecter.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            # Lance un serveur local et ouvre le navigateur pour l'auth
            creds = flow.run_local_server(port=0)
            
        # Sauvegarde du token pour la prochaine fois
        with open('token.json', 'w') as token_file:
            token_file.write(creds.to_json())
            
    return creds

def get_header(headers, name):
    """Extrait une valeur spécifique des headers de l'email."""
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return "Inconnu"

def get_email_body(payload):
    """Extrait le corps de l'email en privilégiant le format HTML."""
    if 'parts' in payload:
        # On cherche d'abord le HTML
        for part in payload['parts']:
            if part['mimeType'] == 'text/html':
                if 'data' in part['body']:
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
            elif part['mimeType'] == 'multipart/alternative' or part['mimeType'] == 'multipart/related':
                body = get_email_body(part)
                if body:
                    return body
        # Si on n'a pas trouvé de HTML, on cherche le texte brut
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
    elif 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
    
    return ""

def main():
    print("Vérification de l'authentification...")
    try:
        creds = authenticate_gmail()
        service = build('gmail', 'v1', credentials=creds)
        
        # Requête de recherche (identique à la barre de recherche Gmail)
        search_query = "from:tldrnewsletter.com"
        print(f"Recherche des emails avec la requête : '{search_query}'")
        
        # Appeler l'API Gmail
        results = service.users().messages().list(userId='me', q=search_query, maxResults=5).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("Aucun message trouvé.")
            return
            
        print(f"\n✅ {len(messages)} messages trouvés :\n")
        
        # Création du dossier de destination
        output_dir = os.path.join('data', 'raw', 'newsletter', 'tldr-ai')
        os.makedirs(output_dir, exist_ok=True)
        
        for i, message in enumerate(messages, 1):
            # Récupérer le message complet pour avoir le corps (format=full)
            msg_details = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            
            payload = msg_details['payload']
            headers = payload['headers']
            subject = get_header(headers, 'Subject')
            date_str = get_header(headers, 'Date')
            
            # Formatage de la date
            try:
                date_obj = parsedate_to_datetime(date_str)
                date_formatted = date_obj.strftime("%d/%m/%Y %H:%M")
                file_date = date_obj.strftime("%Y%m%d")
            except:
                date_formatted = date_str
                file_date = "YYYYMMDD"
                
            # Extraction du corps du message
            body = get_email_body(payload)
            
            # Sauvegarde dans un fichier HTML
            # On utilise une convention <YYYYMMDD>_tldr-ai.html (en ajoutant l'ID pour éviter d'écraser s'il y en a plusieurs le même jour)
            filename = f"{file_date}_tldr-ai_{message['id']}.html"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"<!-- Subject: {subject} -->\n")
                f.write(f"<!-- Date: {date_formatted} -->\n")
                f.write(f"<!-- ID: {message['id']} -->\n")
                f.write(body)
                
            print(f"[{i}] {date_formatted}")
            print(f"    Sujet : {subject}")
            print(f"    Fichier : {filepath}")
            print("-" * 50)
            
    except HttpError as error:
        print(f"❌ Une erreur API est survenue : {error}")
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")

if __name__ == '__main__':
    main()
