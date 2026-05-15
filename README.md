# Omnivigie (L'Assistant Veille "Omnimessie")

Omnivigie est un assistant personnel automatisé conçu pour réaliser une **veille technologique sur mesure** (orientée Data & Intelligence Artificielle) avec un minimum d'effort manuel.

Son objectif final est de collecter automatiquement des newsletters, d'en extraire les articles, d'évaluer leur pertinence selon des critères personnalisés via une IA, et d'injecter les meilleurs contenus dans **Google NotebookLM** afin de générer un podcast de synthèse.

## 🏗️ Architecture et État d'Avancement

Le projet est construit de manière modulaire. Plusieurs programmes ont été écrits itérativement pour valider chaque brique technique.

### La Pipeline Actuelle

1. **Collecte des Newsletters (`06_test_gmail_api.py`)** : 
   - Se connecte à la boîte de réception Gmail via l'API officielle Google (OAuth 2.0).
   - Récupère les emails bruts de la newsletter ciblée (actuellement `TLDR AI`) et les sauvegarde au format HTML localement (`data/raw/`).

2. **Extraction et Structuration (`07_parse_tldr.py`)** :
   - Parse le code HTML de la newsletter (avec `BeautifulSoup`).
   - Sépare les différents articles, nettoie les liens de tracking, et sauvegarde les informations essentielles (titre, lien direct, temps de lecture, résumé) dans une base de données **SQLite** (`data/refined/newsletter.db`).
   - Assure un dédoublonnage strict des URLs.

3. **Qualification par l'IA (`08_qualify_articles.py`)** :
   - Étape cruciale pour éviter l'infobésité.
   - Applique d'abord un filtre métier : exclusion automatique des articles sponsorisés ou trop courts (< 5 minutes).
   - Utilise ensuite le modèle **Google Gemini** (`gemini-3.1-flash-lite` via `google-genai`) en lui envoyant la liste des articles restants en un seul bloc (batch).
   - L'IA évalue chaque article face aux critères d'intérêts de l'utilisateur et met à jour la base de données (`is_interesting`, `tags`, `explanation`).

### Briques Précédentes & Prochaines Étapes
- Les scripts `01` à `04` ont servi de preuve de concept pour la manipulation de l'API communautaire `notebooklm-py` et de moteurs de recherche (`Tavily`).
- Le script `05_orchestrateur.py` est l'ébauche de l'automatisation de bout en bout (basée initialement sur Tavily, en cours de remplacement par la logique Newsletter).
- **Prochaine étape majeure** : Unifier le flux pour que les articles validés par le script `08` soient automatiquement injectés dans un nouveau carnet NotebookLM pour lancer la génération du podcast audio (Audio Overview).

## ⚙️ Configuration & Installation

Le projet nécessite un environnement Python et plusieurs fichiers de configuration non versionnés pour des raisons de sécurité :

1. **Dépendances** : `pip install -r requirements.txt`
2. **`.env`** : Contient votre clé d'API Google Gemini (`GEMINI_API_KEY`). Voir `.env.example`.
3. **`credentials.json`** : Clé OAuth 2.0 Client ID téléchargée depuis Google Cloud Console pour l'API Gmail.
4. **`criteria.md`** : Vos critères d'intérêts en langage naturel (Thèmes pertinents et thèmes à exclure), utilisés par le LLM pour le tri.
5. **`llm_config.json`** : Configuration technique du LLM (nom du modèle, température).

---
*Que la sagesse de l'Omnimessie guide cette veille technologique.*
