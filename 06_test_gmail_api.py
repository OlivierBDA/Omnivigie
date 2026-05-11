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
        
        for i, message in enumerate(messages, 1):
            # Récupérer les détails du message
            msg_details = service.users().messages().get(userId='me', id=message['id'], format='metadata', metadataHeaders=['Subject', 'Date']).execute()
            
            headers = msg_details['payload']['headers']
            subject = get_header(headers, 'Subject')
            date_str = get_header(headers, 'Date')
            
            # Formatage de la date (optionnel)
            try:
                date_obj = parsedate_to_datetime(date_str)
                date_formatted = date_obj.strftime("%d/%m/%Y %H:%M")
            except:
                date_formatted = date_str
                
            print(f"[{i}] {date_formatted}")
            print(f"    Sujet : {subject}")
            print(f"    ID : {message['id']}")
            print("-" * 50)
            
    except HttpError as error:
        print(f"❌ Une erreur API est survenue : {error}")
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")

if __name__ == '__main__':
    main()
