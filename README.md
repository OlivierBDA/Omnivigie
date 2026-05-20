# Omnivigie (L'Assistant Veille "Omnimessie")

Omnivigie est un assistant personnel automatisé conçu pour réaliser une **veille technologique sur mesure** (orientée Data & Intelligence Artificielle) avec un minimum d'effort manuel.

Son objectif final est de collecter automatiquement des newsletters, d'en extraire les articles, d'évaluer leur pertinence selon des critères stricts via une IA (Gemini), de les regrouper par thèmes de manière interactive, et d'injecter les meilleurs contenus dans **Google NotebookLM** afin de générer un podcast analytique de synthèse (Deep Dive).

## 🏗️ Architecture et Pipeline

Le projet a été refondu dans une architecture modulaire et robuste. La suite logicielle s'exécute de manière unitaire ou via un orchestrateur global.

### La Pipeline (via `orchestrator.py`)

0. **Authentification (`auto_login_notebooklm`)** : L'orchestrateur lance une session `notebook login` en tâche de fond et valide la connexion automatiquement (récupération des cookies) pour éviter toute expiration de session.

1. **Collecte des Newsletters (`fetch_newsletters.py`)** : 
   - Se connecte à la boîte de réception Gmail via l'API officielle Google (OAuth 2.0).
   - Ne récupère que les nouveaux emails (filtre `after:timestamp` basé sur l'historique en base de données).
   - Extrait le HTML et le sauvegarde localement (`data/raw/`).
   - Maintient l'historique de téléchargement dans la table SQLite `email`.

2. **Extraction et Structuration (`parse_newsletters.py`)** :
   - Parse le code HTML des nouvelles newsletters avec `BeautifulSoup`.
   - Sépare les différents articles, nettoie les liens de tracking, et sauvegarde les informations essentielles (titre, lien direct, temps de lecture, résumé) dans la table SQLite `tldr_ai`.
   - Déplace les fichiers HTML traités vers le dossier `processed/` pour éviter les doublons.

3. **Qualification par l'IA (`qualify_articles.py`)** :
   - Applique un filtre métier : exclusion automatique des articles sponsorisés ou trop courts (< 5 minutes), marqués comme `is_processed=1`.
   - Utilise le modèle **Google Gemini** (`gemini-3.1-flash-lite` via `google-genai`) en lui envoyant la liste des articles restants (batch).
   - Contraint l'IA à qualifier l'article et à lui attribuer des tags obligatoirement piochés dans la liste de `themes.json`.

4. **Création Thématique (`create_themed_notebook.py`)** (Interactif) :
   - Récupère l'ensemble des articles validés par l'IA et non encore traités (`is_processed=0`).
   - Affiche un menu listant l'intégralité des thèmes définis et le nombre d'articles en attente.
   - Demande à l'utilisateur de sélectionner un thème à synthétiser.
   - Crée le carnet NotebookLM (`[AI] YYYY-MM-DD TLDR-{Thème}`), y ajoute les URLs, et marque les articles concernés comme `is_processed=1`.

5. **Génération du Mindmap (`generate_mindmap.py`)** :
   - Requête l'API de NotebookLM pour générer une carte mentale (Mindmap) de l'ensemble du carnet.
   - Patiente (polling) jusqu'à sa disponibilité et la télécharge au format JSON.

6. **Transformation Sémantique JSON -> Graph (`json_to_graph.py`)** :
   - Analyse la Mindmap JSON avec l'IA (Gemini).
   - Convertit les informations non structurées en un formalisme Graphe stricte (Noeuds et Relations) en suivant l'ontologie métier (`graphModel.txt`).
   - Propose de nouveaux concepts (auto-apprentissage du modèle).

7. **Ingestion dans la base Neo4j (`neo4j_ingestion.py`)** :
   - Se connecte à la base de données orientée graphe Neo4j locale.
   - Intègre les nœuds et relations (MERGE) issus de la Mindmap.
   - Insère les nouveaux concepts identifiés par l'IA directement dans le schéma de référence (`graphModel.txt`) pour enrichir les itérations futures.

8. **Génération du Podcast (`generate_podcast.py`)** :
   - Lance la génération d'un fichier audio (format long / deep-dive analytique) ciblé pour des architectes et ingénieurs.
   - L'action est asynchrone ("fire and forget"), le programme s'arrête ensuite.

## ⚙️ Configuration & Installation

Le projet nécessite un environnement Python et plusieurs fichiers de configuration non versionnés pour des raisons de sécurité :

1. **Dépendances** : `pip install -r requirements.txt`
2. **`.env`** : Contient votre clé d'API Google Gemini (`GEMINI_API_KEY`). Voir `.env.example`.
3. **`credentials.json`** : Clé OAuth 2.0 Client ID téléchargée depuis Google Cloud Console pour l'API Gmail. Le token d'accès généré sera stocké dans `token.json`.
4. **`themes.json`** : La liste exclusive des thèmes autorisés pour l'IA et pour la création des carnets (Ex: "Agents Autonomes & Agentic").
5. **`criteria.md`** : Vos critères d'intérêts en langage naturel, utilisés par le LLM pour exclure ou valider la pertinence technique.
6. **`llm_config.json`** : Configuration technique du LLM (nom du modèle, température).
7. **`graphModel.txt`** : Ontologie / Schéma dynamique du graphe de connaissance Neo4j. Le LLM lit et modifie ce fichier de manière autonome.

## 🚀 Utilisation Courante

Lancez simplement le programme maître. Il s'occupera du téléchargement, du tri intelligent, et vous demandera quel thème vous souhaitez écouter aujourd'hui :

```bash
python .\orchestrator.py
```

---
*Que la sagesse de l'Omnimessie guide cette veille technologique.*
