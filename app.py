import os
import sys
import json
import asyncio
import sqlite3
import contextlib
import io
import subprocess
from datetime import datetime
import streamlit as st

# Import des modules existants du projet
import fetch_newsletters
import parse_newsletters
import qualify_articles
import create_themed_notebook
import generate_mindmap
import json_to_graph
import neo4j_ingestion
import generate_podcast

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Omnivigie - Assistant Veille IA",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# DESIGN SYSTEM & STYLES (PREMIUM DARK NEON DESIGN)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Space+Grotesk:wght@400;600&display=swap');
    
    /* Force le thème sombre cosmique pour l'ensemble de l'application (SaaS-like) */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #090d16 !important;
        color: #e2e8f0 !important;
    }
    
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
        background-color: #121b2d !important;
        color: #cbd5e1 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    h1, h2, h3, .main-title {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        color: #ffffff !important;
    }
    
    /* Titre Néon Gradient */
    .main-title {
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 50%, #7f00ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        margin-bottom: 0.5rem;
        text-shadow: 0px 0px 20px rgba(0, 242, 254, 0.2);
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #94a3b8;
        margin-bottom: 2rem;
    }
    
    /* Cartes Métriques Premium en Fond Solide Épais */
    .metric-card {
        background-color: #121b2d !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
        transition: all 0.3s ease-in-out;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: rgba(0, 242, 254, 0.4) !important;
        box-shadow: 0 12px 40px 0 rgba(0, 242, 254, 0.25);
    }
    
    .metric-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #94a3b8 !important; /* Gris clair très visible */
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2.3rem;
        font-weight: 700;
        color: #ffffff !important; /* Blanc pur */
        text-shadow: 0px 2px 4px rgba(0,0,0,0.5);
    }
    
    .metric-footer {
        font-size: 0.8rem;
        color: #64748b !important;
        margin-top: 0.5rem;
    }
    
    /* Cartes Articles en Fond Sombre Épais */
    .article-card {
        background-color: #121b2d !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.25);
        transition: all 0.2s ease;
    }
    
    .article-card:hover {
        border-color: rgba(127, 0, 255, 0.4) !important;
        box-shadow: 0 4px 25px 0 rgba(127, 0, 255, 0.2);
        transform: scale(1.005);
    }
    
    .article-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #38bdf8 !important; /* Bleu clair vif contrasté */
        text-decoration: none;
        margin-bottom: 0.5rem;
        display: block;
    }
    
    .article-title:hover {
        color: #00f2fe !important;
        text-decoration: underline;
    }
    
    .article-meta {
        display: flex;
        gap: 1rem;
        font-size: 0.85rem;
        color: #94a3b8 !important;
        margin-bottom: 0.75rem;
        flex-wrap: wrap;
    }
    
    /* Badges de thématiques et de temps de lecture à haut contraste */
    .badge {
        background: rgba(56, 189, 248, 0.15) !important;
        color: #38bdf8 !important;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .badge-time {
        background: rgba(245, 158, 11, 0.15) !important;
        color: #fbbf24 !important; /* Jaune d'or lumineux */
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
    }
    
    .badge-theme {
        background: rgba(168, 85, 247, 0.15) !important;
        color: #c084fc !important; /* Magenta/Violet lumineux */
        border: 1px solid rgba(168, 85, 247, 0.3) !important;
    }
    
    .article-summary {
        font-size: 0.92rem;
        color: #cbd5e1 !important; /* Gris de lecture optimal */
        line-height: 1.6;
    }
    
    /* Console de logs */
    .log-box {
        background: #04060a !important;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        font-family: 'Fira Code', 'Courier New', monospace;
        font-size: 0.85rem;
        color: #00ff66 !important;
        padding: 1rem;
        max-height: 350px;
        overflow-y: auto;
    }
    
    /* Statuts diagnostics */
    .status-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    .status-ok {
        background: rgba(16, 185, 129, 0.15) !important;
        color: #34d399 !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }
    
    .status-err {
        background: rgba(239, 68, 68, 0.15) !important;
        color: #f87171 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# CAPTURE DE FLUX LOGS POUR STREAMLIT
# ---------------------------------------------------------
class StreamToStreamlit:
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.buffer = io.StringIO()

    def write(self, text):
        # Filtrer certains sauts de lignes pour éviter d'inonder le log
        self.buffer.write(text)
        self.placeholder.code(self.buffer.getvalue(), language="text")

    def flush(self):
        pass

@contextlib.contextmanager
def st_capture(placeholder):
    stream = StreamToStreamlit(placeholder)
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = stream
    sys.stderr = stream
    try:
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

# ---------------------------------------------------------
# GESTION DES DIAGNOSTICS & CONNEXIONS
# ---------------------------------------------------------
async def check_notebooklm_session():
    """Vérifie si la session NotebookLM locale est active et valide."""
    try:
        from notebooklm.client import NotebookLMClient
        async with await NotebookLMClient.from_storage() as client:
            # Effectuer un appel d'API léger pour valider le token
            await client.notebooks.list()
            return True, "Session active dans NotebookLM !"
    except Exception as e:
        return False, f"Session expirée ou non configurée : {e}"

def check_neo4j_connection():
    """Vérifie la connexion locale ou distante à la base Neo4j."""
    from neo4j import GraphDatabase
    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "omnigraph")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        return True, "Base Neo4j connectée avec succès !"
    except Exception as e:
        return False, f"Impossible de se connecter à Neo4j (Bolt/Port 7687). Vérifiez que Neo4j Desktop tourne. {e}"

def run_notebooklm_login_process():
    """Déclenche la commande 'notebook login' en tâche de fond pour l'utilisateur."""
    try:
        # Lance la commande d'authentification en redirigeant l'entrée standard
        process = subprocess.Popen(
            [sys.executable, "-m", "notebooklm", "login"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        st.session_state.login_process = process
        return True
    except Exception as e:
        st.error(f"Erreur lors du lancement de la commande d'authentification : {e}")
        return False

# ---------------------------------------------------------
# ACCÈS AUX DONNÉES & STATISTIQUES
# ---------------------------------------------------------
DB_FILE = os.path.join('data', 'refined', 'newsletter.db')

def get_db_stats():
    """Calcule les métriques clés de la base SQLite."""
    stats = {
        'total_emails': 0,
        'last_sync_date': "Aucune synchronisation",
        'total_articles': 0,
        'pending_articles': 0,
        'interesting_articles': 0,
        'total_notebooks': 0
    }
    
    if not os.path.exists(DB_FILE):
        return stats
        
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Total Emails
        cursor.execute("SELECT COUNT(*) FROM email")
        stats['total_emails'] = cursor.fetchone()[0]
        
        # Last Sync
        cursor.execute("SELECT MAX(date_received) FROM email")
        last_sync = cursor.fetchone()[0]
        if last_sync:
            stats['last_sync_date'] = datetime.fromtimestamp(last_sync).strftime('%d/%m/%Y à %H:%M:%S')
            
        # Total Articles
        cursor.execute("SELECT COUNT(*) FROM tldr_ai")
        stats['total_articles'] = cursor.fetchone()[0]
        
        # Pending articles
        cursor.execute("SELECT COUNT(*) FROM tldr_ai WHERE is_interesting = 1 AND is_processed = 0")
        stats['pending_articles'] = cursor.fetchone()[0]
        
        # Total Interesting
        cursor.execute("SELECT COUNT(*) FROM tldr_ai WHERE is_interesting = 1")
        stats['interesting_articles'] = cursor.fetchone()[0]
        
        # Total Notebooks
        cursor.execute("SELECT COUNT(*) FROM notebook")
        stats['total_notebooks'] = cursor.fetchone()[0]
        
        conn.close()
    except Exception as e:
        pass
        
    return stats

def get_neo4j_stats():
    """Calcule le nombre de nœuds et relations dans Neo4j si connecté."""
    stats = {'nodes': 0, 'relations': 0}
    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "omnigraph")
    
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            stats['nodes'] = session.run("MATCH (n) RETURN count(n) as count").single()['count']
            stats['relations'] = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
        driver.close()
    except:
        pass # Silencieux en cas de non connexion
    return stats

def get_latest_qualified_articles(limit=10):
    """Récupère les derniers articles pertinents qualifiés par l'IA."""
    if not os.path.exists(DB_FILE):
        return []
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT newsletter_date, title, url, reading_time, summary, tags, explanation 
            FROM tldr_ai 
            WHERE is_interesting = 1 
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        return []

# ---------------------------------------------------------
# INITIALISATION DE L'ÉTAT D'APPLICATION (SESSION STATE)
# ---------------------------------------------------------
if 'nb_ok' not in st.session_state:
    st.session_state.nb_ok = False
    st.session_state.nb_msg = "Diagnostic non lancé"
if 'neo_ok' not in st.session_state:
    st.session_state.neo_ok = False
    st.session_state.neo_msg = "Diagnostic non lancé"
if 'current_notebook' not in st.session_state:
    st.session_state.current_notebook = ""
if 'login_process' not in st.session_state:
    st.session_state.login_process = None
if 'acquisition_results' not in st.session_state:
    st.session_state.acquisition_results = None
if 'notebook_creation_results' not in st.session_state:
    st.session_state.notebook_creation_results = None
if 'neo4j_ingestion_results' not in st.session_state:
    st.session_state.neo4j_ingestion_results = None
if 'podcast_generation_results' not in st.session_state:
    st.session_state.podcast_generation_results = None

# Diagnostic au démarrage (une fois par session ou sur action)
def run_diagnostics():
    with st.spinner("Exécution des vérifications système..."):
        # 1. NotebookLM
        nb_ok, nb_msg = asyncio.run(check_notebooklm_session())
        st.session_state.nb_ok = nb_ok
        st.session_state.nb_msg = nb_msg
        
        # 2. Neo4j
        neo_ok, neo_msg = check_neo4j_connection()
        st.session_state.neo_ok = neo_ok
        st.session_state.neo_msg = neo_msg

# Effectuer le diagnostic si non fait
if st.session_state.nb_msg == "Diagnostic non lancé":
    run_diagnostics()

# ---------------------------------------------------------
# SIDEBAR : CONTROLES ET STATUTS GLOBAUX
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #00f2fe; margin-bottom: 0px;'>🌌 O M N I V I G I E</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 0.8rem; color: #64748b;'>L'Assistant Veille \"Omnimessie\"</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.subheader("🛡️ Diagnostics Système")
    
    # Indicateur NotebookLM
    if st.session_state.nb_ok:
        st.markdown('<div class="status-indicator status-ok">🟢 NotebookLM : Connecté</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-indicator status-err">🔴 NotebookLM : Non Connecté</div>', unsafe_allow_html=True)
        st.caption(f"⚠️ {st.session_state.nb_msg}")
        
    # Indicateur Neo4j
    if st.session_state.neo_ok:
        st.markdown('<div class="status-indicator status-ok">🟢 Neo4j : Connecté</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-indicator status-err">🔴 Neo4j : Non Connecté</div>', unsafe_allow_html=True)
        st.caption(f"⚠️ {st.session_state.neo_msg}")
        
    if st.session_state.login_process is not None:
        st.warning("🔌 Connexion active : connectez-vous dans le navigateur puis cliquez sur 'Valider' ci-dessous.")

    # Boutons d'action diagnostics
    col_diag1, col_diag2 = st.columns(2)
    with col_diag1:
        if st.button("🔄 Rafraîchir", help="Tester à nouveau les connexions"):
            run_diagnostics()
            st.rerun()
            
    with col_diag2:
        if st.session_state.login_process is not None:
            # Bouton de validation si un processus d'authentification est en cours
            if st.button("✅ Valider", help="Confirmer la connexion et enregistrer les cookies"):
                try:
                    process = st.session_state.login_process
                    # Envoyer un retour à la ligne (Entrée) dans l'entrée standard du processus
                    process.stdin.write("\n")
                    process.stdin.flush()
                    # Attendre la fin
                    process.communicate(timeout=10)
                    st.success("Session validée avec succès !")
                except Exception as e:
                    st.error(f"Erreur lors de la validation : {e}")
                finally:
                    st.session_state.login_process = None
                    run_diagnostics()
                    st.rerun()
        elif not st.session_state.nb_ok:
            if st.button("🔑 Connexion", help="Lancer notebook login dans votre navigateur local"):
                if run_notebooklm_login_process():
                    st.info("Navigateur ouvert. Complétez la connexion puis cliquez sur le bouton vert 'Valider' ci-dessus.")
                    st.rerun()
                    
    st.markdown("---")
    st.markdown("### ⚙️ Quick status")
    stats = get_db_stats()
    st.write(f"📅 **Dernière Synchro :** \n{stats['last_sync_date']}")
    
    neo_stats = get_neo4j_stats()
    st.write(f"🧬 **Graphe Neo4j :** \n{neo_stats['nodes']} nœuds / {neo_stats['relations']} liens")

# ---------------------------------------------------------
# APPLICATION PRINCIPALE : HEADER ET TABS
# ---------------------------------------------------------
st.markdown("<h1 class='main-title'>Omnivigie Tech Watch</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Dashboard intelligent et pipeline de curation automatisé pour NotebookLM et base de connaissances Neo4j.</p>", unsafe_allow_html=True)

tab_dash, tab_pipe, tab_config = st.tabs([
    "📊 Tableau de Bord", 
    "🚀 Lancer la Veille", 
    "🔧 Configuration & Thèmes"
])

# ---------------------------------------------------------
# ONGLET 1 : TABLEAU DE BORD
# ---------------------------------------------------------
with tab_dash:
    # 1. Cartes de Métriques Clés
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Emails Reçus</div>
            <div class="metric-value">{stats['total_emails']}</div>
            <div class="metric-footer">Dernière synchro : {stats['last_sync_date'].split(' à ')[0]}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Articles Extraits</div>
            <div class="metric-value">{stats['total_articles']}</div>
            <div class="metric-footer">{stats['interesting_articles']} qualifiés intéressants par IA</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">En Attente Curation</div>
            <div class="metric-value" style="color: #f59e0b;">{stats['pending_articles']}</div>
            <div class="metric-footer">Articles qualifiés non encore traités</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Carnets NotebookLM</div>
            <div class="metric-value" style="color: #a855f7;">{stats['total_notebooks']}</div>
            <div class="metric-footer">Carnets synchronisés en base de données</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Liste des derniers articles qualifiés intéressants
    st.markdown("### 🔥 Articles Récemment Qualifiés d'Intérêt Majeur")
    st.markdown("Voici les articles validés par Gemini qui reflètent vos critères technologiques.")
    
    articles = get_latest_qualified_articles(10)
    if not articles:
        st.info("Aucun article pertinent trouvé pour le moment. Lancez le processus de récupération et qualification !")
    else:
        for newsletter_date, title, url, reading_time, summary, tags, explanation in articles:
            # Formater la date YYYYMMDD -> YYYY-MM-DD
            formatted_date = f"{newsletter_date[:4]}-{newsletter_date[4:6]}-{newsletter_date[6:]}" if len(newsletter_date) == 8 else newsletter_date
            
            # Badges
            badges_html = ""
            if tags:
                for tag in tags.split(','):
                    badges_html += f'<span class="badge badge-theme">{tag.strip()}</span> '
            if reading_time:
                badges_html += f'<span class="badge badge-time">⏳ {reading_time}</span>'
                
            st.markdown(f"""
            <div class="article-card">
                <a class="article-title" href="{url}" target="_blank">{title}</a>
                <div class="article-meta">
                    <span>📅 {formatted_date}</span>
                    {badges_html}
                </div>
                <div class="article-summary">{summary}</div>
                <div style="font-size: 0.82rem; color: #34d399; margin-top: 0.5rem; font-style: italic; font-weight: 500;">
                    💡 Pourquoi : {explanation}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ---------------------------------------------------------
# ONGLET 2 : LANCEUR DE PIPELINE (PIPELINE RUNNER)
# ---------------------------------------------------------
with tab_pipe:
    st.markdown("## ⚙️ Pipeline Omnivigie")
    st.markdown("Exécutez les étapes successives pour traiter les actualités, créer votre carnet et générer vos podcasts.")
    
    # Bloqueurs si état au rouge
    has_blocker = not st.session_state.nb_ok or not st.session_state.neo_ok
    if has_blocker:
        st.warning("""
        ⚠️ **Attention : Dysfonctionnement système détecté**  
        * L'authentification NotebookLM ou la connexion locale à la base Neo4j est actuellement inactive (au rouge dans la barre latérale).
        * Vous pouvez tout de même synchroniser et qualifier vos articles, mais les étapes de carnet, mindmap et graph Neo4j risquent d'échouer.
        * Veuillez vérifier que Neo4j Desktop est lancé et que vos cookies NotebookLM sont valides.
        """)

    step_tab1, step_tab2, step_tab3 = st.tabs([
        "📥 1. Acquisition & Tri (Gmail -> IA)", 
        "📚 2. Curation & Carnet NotebookLM", 
        "🎧 3. Graphe Neo4j & Podcast Audio"
    ])
    
    # --- ÉTAPE A : ACQUISITION & IA TRI ---
    with step_tab1:
        st.subheader("Étape 1 à 3 : Récupération des Emails, Extraction et Qualification par Gemini")
        st.markdown("""
        Ce bloc se connecte à Gmail, extrait le HTML des newsletters TLDR, parse les métadonnées et évalue la pertinence de chaque article selon votre fichier de critères.
        """)
        
        # Rendu de l'encart de succès persistant après exécution
        if st.session_state.acquisition_results is not None:
            res = st.session_state.acquisition_results
            st.markdown(f"""
            <div class="status-indicator status-ok" style="flex-direction: column; align-items: flex-start; gap: 0.5rem; padding: 1.25rem;">
                <div style="font-weight: 700; font-size: 1.2rem; color: #34d399;">
                    🎉 {res['title']}
                </div>
                <div style="font-size: 0.95rem; color: #cbd5e1; line-height: 1.6;">
                    {res['details']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("📋 Consulter les logs d'exécution de ce processus", expanded=False):
                st.code(res['logs'], language="text")
                
            col_clear_btn, _ = st.columns([0.2, 0.8])
            with col_clear_btn:
                if st.button("🗑️ Masquer les résultats", key="btn_clear_results"):
                    st.session_state.acquisition_results = None
                    st.rerun()
            st.markdown("---")
            
        # Enchaînement complet
        if st.button("🔮 Lancer l'acquisition complète (Recommandé)", key="btn_full_acquire", type="primary"):
            # Calcul des métriques avant
            stats_before = get_db_stats()
            emails_before = stats_before['total_emails']
            articles_before = stats_before['total_articles']
            pending_before = stats_before['pending_articles']
            
            log_placeholder = st.empty()
            stream = StreamToStreamlit(log_placeholder)
            
            # Capturer les logs
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = stream
            sys.stderr = stream
            
            try:
                print(">>> DEBUT DU PROCESSUS D'ACQUISITION GLOBALE <<<")
                # 1. Gmail Fetch
                print("\n--- [ÉTAPE 1/3] RÉCUPÉRATION DES EMAILS DEPUIS GMAIL ---")
                fetch_newsletters.run()
                
                # 2. Parse HTML
                print("\n--- [ÉTAPE 2/3] EXTRACTION ET NETTOYAGE DES ARTICLES HTML ---")
                parse_newsletters.run()
                
                # 3. Qualify
                print("\n--- [ÉTAPE 3/3] QUALIFICATION ET BATCHING SEMANTIQUE GEMINI ---")
                qualify_articles.run()
                print("\n>>> FIN DE L'ACQUISITION GLOBALE AVEC SUCCES ! <<<")
            except Exception as e:
                print(f"\n[ERREUR CRITIQUE] {e}")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
            # Calcul des métriques après
            stats_after = get_db_stats()
            new_emails = stats_after['total_emails'] - emails_before
            new_articles = stats_after['total_articles'] - articles_before
            new_pending = stats_after['pending_articles'] - pending_before
            
            st.session_state.acquisition_results = {
                'title': f"Acquisition complète terminée avec succès à {datetime.now().strftime('%H:%M:%S')} !",
                'details': (
                    f"• 📥 <b>Nouveaux emails récupérés</b> : {new_emails}<br>"
                    f"• ✂️ <b>Nouveaux articles extraits de Gmail</b> : {new_articles}<br>"
                    f"• 🧠 <b>Articles qualifiés pertinents (en attente)</b> : {new_pending}"
                ),
                'logs': stream.buffer.getvalue()
            }
            st.rerun()
            
        st.markdown("---")
        st.markdown("### Exécution étape par étape (Avancé)")
        col_step1, col_step2, col_step3 = st.columns(3)
        
        with col_step1:
            if st.button("📥 Étape 1 : Gmail Sync", use_container_width=True):
                stats_before = get_db_stats()
                emails_before = stats_before['total_emails']
                
                log_placeholder = st.empty()
                stream = StreamToStreamlit(log_placeholder)
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = stream, stream
                try:
                    fetch_newsletters.run()
                except Exception as e:
                    print(f"\n[ERREUR] {e}")
                finally:
                    sys.stdout, sys.stderr = old_stdout, old_stderr
                    
                stats_after = get_db_stats()
                new_emails = stats_after['total_emails'] - emails_before
                
                st.session_state.acquisition_results = {
                    'title': f"Synchronisation Gmail terminée à {datetime.now().strftime('%H:%M:%S')} !",
                    'details': f"• 📥 <b>Nouveaux emails récupérés et stockés</b> : {new_emails}",
                    'logs': stream.buffer.getvalue()
                }
                st.rerun()
                
        with col_step2:
            if st.button("✂️ Étape 2 : Parse HTML", use_container_width=True):
                stats_before = get_db_stats()
                articles_before = stats_before['total_articles']
                
                log_placeholder = st.empty()
                stream = StreamToStreamlit(log_placeholder)
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = stream, stream
                try:
                    parse_newsletters.run()
                except Exception as e:
                    print(f"\n[ERREUR] {e}")
                finally:
                    sys.stdout, sys.stderr = old_stdout, old_stderr
                    
                stats_after = get_db_stats()
                new_articles = stats_after['total_articles'] - articles_before
                
                st.session_state.acquisition_results = {
                    'title': f"Parsing des newsletters terminé à {datetime.now().strftime('%H:%M:%S')} !",
                    'details': f"• ✂️ <b>Nouveaux articles extraits en base de données</b> : {new_articles}",
                    'logs': stream.buffer.getvalue()
                }
                st.rerun()
                
        with col_step3:
            if st.button("🧠 Étape 3 : IA Qualify", use_container_width=True):
                stats_before = get_db_stats()
                pending_before = stats_before['pending_articles']
                
                log_placeholder = st.empty()
                stream = StreamToStreamlit(log_placeholder)
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = stream, stream
                try:
                    qualify_articles.run()
                except Exception as e:
                    print(f"\n[ERREUR] {e}")
                finally:
                    sys.stdout, sys.stderr = old_stdout, old_stderr
                    
                stats_after = get_db_stats()
                new_pending = stats_after['pending_articles'] - pending_before
                
                st.session_state.acquisition_results = {
                    'title': f"Qualification IA terminée à {datetime.now().strftime('%H:%M:%S')} !",
                    'details': f"• 🧠 <b>Nouveaux articles d'intérêt sémantique identifiés (en attente)</b> : {new_pending}",
                    'logs': stream.buffer.getvalue()
                }
                st.rerun()

    # --- ÉTAPE B : INTERACTIVE NOTEBOOKLM CREATION ---
    with step_tab2:
        st.subheader("Étape 4 : Création du Carnet dans Google NotebookLM")
        st.markdown("""
        Sélectionnez l'une de vos thématiques préférées pour voir les articles qualifiés intéressants et en attente. 
        **Vous pouvez désélectionner manuellement certains articles** avant d'envoyer la commande à NotebookLM.
        """)
        
        # Rendu de l'encart de succès persistant après exécution
        if st.session_state.notebook_creation_results is not None:
            res = st.session_state.notebook_creation_results
            st.markdown(f"""
            <div class="status-indicator status-ok" style="flex-direction: column; align-items: flex-start; gap: 0.5rem; padding: 1.25rem;">
                <div style="font-weight: 700; font-size: 1.2rem; color: #34d399;">
                    🎉 {res['title']}
                </div>
                <div style="font-size: 0.95rem; color: #cbd5e1; line-height: 1.6;">
                    {res['details']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("📋 Consulter les logs d'exécution de création du carnet", expanded=False):
                st.code(res['logs'], language="text")
                
            col_clear_btn, _ = st.columns([0.2, 0.8])
            with col_clear_btn:
                if st.button("🗑️ Masquer les résultats", key="btn_clear_nb_results"):
                    st.session_state.notebook_creation_results = None
                    st.rerun()
            st.markdown("---")
        
        if not os.path.exists(DB_FILE):
            st.info("Aucune base de données trouvée. Lancez l'étape d'acquisition d'abord.")
        else:
            # Récupérer les articles
            pending_articles = create_themed_notebook.get_pending_articles()
            if not pending_articles:
                st.success("🎉 Aucun article pertinent en attente de traitement ! Votre veille est totalement à jour.")
            else:
                # Regrouper par thème
                theme_map = create_themed_notebook.group_by_theme(pending_articles)
                themes_list = create_themed_notebook.load_themes()
                
                # Proposer uniquement les thèmes avec articles
                active_themes = [t for t in themes_list if len(theme_map.get(t, [])) > 0]
                
                if not active_themes:
                    st.info("Les articles en attente n'ont aucun thème défini ou ne correspondent pas aux thèmes configurés.")
                else:
                    selected_theme = st.selectbox(
                        "Choisissez la thématique pour votre carnet de veille :",
                        options=active_themes,
                        format_func=lambda x: f"{x} ({len(theme_map.get(x, []))} articles en attente)"
                    )
                    
                    st.markdown(f"### Articles disponibles pour le thème : **{selected_theme}**")
                    st.caption("Décochez les articles que vous souhaitez ignorer ou reporter à plus tard.")
                    
                    articles_in_theme = theme_map[selected_theme]
                    selected_article_flags = {}
                    
                    # Rendu interactif en forme de cartes avec checkbox
                    for art_id, title, url in articles_in_theme:
                        # Retrouver les détails de l'article pour affichage premium
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("SELECT reading_time, summary, explanation FROM tldr_ai WHERE id=?", (art_id,))
                        row = cursor.fetchone()
                        conn.close()
                        
                        reading_time, summary, explanation = row if row else ("", "", "")
                        
                        col_check, col_card = st.columns([0.05, 0.95])
                        with col_check:
                            # Clé unique basée sur l'ID de l'article
                            selected_article_flags[art_id] = st.checkbox("Inclure", value=True, key=f"check_art_{art_id}", label_visibility="collapsed")
                        with col_card:
                            st.markdown(f"""
                            <div class="article-card" style="margin-bottom: 0px; padding: 0.75rem 1rem;">
                                <a class="article-title" style="font-size: 1rem; margin-bottom: 0.25rem;" href="{url}" target="_blank">{title}</a>
                                <div class="article-meta" style="margin-bottom: 0.25rem;">
                                    <span class="badge badge-time">⏳ {reading_time}</span>
                                </div>
                                <div class="article-summary" style="font-size: 0.85rem;">{summary}</div>
                                <div style="font-size: 0.78rem; color: #34d399; margin-top: 0.25rem; font-style: italic; font-weight: 500;">
                                    💡 IA : {explanation}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                    # Nom du carnet suggéré
                    current_time_str = datetime.now().strftime('%Y-%m-%d')
                    default_notebook_name = f"[AI] {current_time_str} TLDR-{selected_theme}"
                    custom_notebook_name = st.text_input("Nom du carnet NotebookLM à créer :", value=default_notebook_name)
                    
                    # Bouton de création
                    if st.button("🚀 Créer le carnet dans NotebookLM", type="primary"):
                        # Filtrer les articles sélectionnés
                        final_articles_to_add = [
                            art for art in articles_in_theme if selected_article_flags[art[0]]
                        ]
                        
                        if not final_articles_to_add:
                            st.error("Erreur : Vous devez sélectionner au moins un article pour créer un carnet.")
                        else:
                            log_placeholder = st.empty()
                            stream = StreamToStreamlit(log_placeholder)
                            old_stdout, old_stderr = sys.stdout, sys.stderr
                            sys.stdout, sys.stderr = stream, stream
                            
                            res_name = None
                            try:
                                # Nous allons redéfinir temporairement create_notebook_from_articles en injectant notre nom de carnet personnalisé
                                async def run_custom_creation():
                                    try:
                                        from notebooklm.client import NotebookLMClient
                                        print(f"\nConnexion à NotebookLM pour créer le carnet '{custom_notebook_name}'...")
                                        async with await NotebookLMClient.from_storage() as client:
                                            nb = await client.notebooks.create(custom_notebook_name)
                                            print(f"Carnet créé avec succès (ID: {nb.id}) !")
                                            
                                            article_ids = []
                                            for i, (art_id, title, url) in enumerate(final_articles_to_add, 1):
                                                print(f"[{i}/{len(final_articles_to_add)}] Ajout de : {title}")
                                                try:
                                                    await client.sources.add_url(nb.id, url)
                                                    article_ids.append(art_id)
                                                except Exception as e:
                                                    print(f" -> Erreur lors de l'ajout de {url} : {e}")
                                                    
                                            print("\nMise à jour de la base de données...")
                                            notebook_id = create_themed_notebook.insert_notebook(custom_notebook_name)
                                            create_themed_notebook.mark_articles_as_processed(article_ids, notebook_id, custom_notebook_name)
                                            print("Base de données mise à jour avec succès.")
                                            print(f"\n[OK] Le carnet '{custom_notebook_name}' est prêt.")
                                            return custom_notebook_name
                                    except Exception as e:
                                        print(f"Erreur NotebookLM : {e}")
                                        return None
                                        
                                res_name = asyncio.run(run_custom_creation())
                            except Exception as e:
                                print(f"\n[ERREUR CRITIQUE] {e}")
                            finally:
                                sys.stdout, sys.stderr = old_stdout, old_stderr
                                
                            if res_name:
                                st.session_state.current_notebook = res_name
                                st.session_state.notebook_creation_results = {
                                    'title': f"Carnet créé avec succès à {datetime.now().strftime('%H:%M:%S')} !",
                                    'details': (
                                        f"• 📚 <b>Carnet NotebookLM créé</b> : {res_name}<br>"
                                        f"• 🔗 <b>Articles injectés avec succès</b> : {len(final_articles_to_add)}"
                                    ),
                                    'logs': stream.buffer.getvalue()
                                }
                                st.balloons()
                                st.rerun()

    # --- ÉTAPE C : AUDIO & GRAPHE INGESTION ---
    with step_tab3:
        st.subheader("Étape 5 à 8 : Mindmap sémantique, ingestion Neo4j & Podcast Audio")
        st.markdown("""
        Une fois votre carnet créé dans NotebookLM, vous pouvez synchroniser sa Mindmap structurée vers votre base Neo4j de graphe de connaissance et lancer la génération d'un Podcast Audio de synthèse.
        """)
        
        # Rendu des encarts de succès persistants
        if st.session_state.neo4j_ingestion_results is not None:
            res = st.session_state.neo4j_ingestion_results
            st.markdown(f"""
            <div class="status-indicator status-ok" style="flex-direction: column; align-items: flex-start; gap: 0.5rem; padding: 1.25rem;">
                <div style="font-weight: 700; font-size: 1.2rem; color: #34d399;">
                    🎉 {res['title']}
                </div>
                <div style="font-size: 0.95rem; color: #cbd5e1; line-height: 1.6;">
                    {res['details']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("📋 Consulter les logs d'ingestion de graphe", expanded=False):
                st.code(res['logs'], language="text")
                
            col_clear_btn, _ = st.columns([0.2, 0.8])
            with col_clear_btn:
                if st.button("🗑️ Masquer les résultats Ingestion", key="btn_clear_neo_results"):
                    st.session_state.neo4j_ingestion_results = None
                    st.rerun()
            st.markdown("---")
            
        if st.session_state.podcast_generation_results is not None:
            res = st.session_state.podcast_generation_results
            st.markdown(f"""
            <div class="status-indicator status-ok" style="flex-direction: column; align-items: flex-start; gap: 0.5rem; padding: 1.25rem;">
                <div style="font-weight: 700; font-size: 1.2rem; color: #34d399;">
                    🎉 {res['title']}
                </div>
                <div style="font-size: 0.95rem; color: #cbd5e1; line-height: 1.6;">
                    {res['details']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("📋 Consulter les logs de génération du podcast", expanded=False):
                st.code(res['logs'], language="text")
                
            col_clear_btn, _ = st.columns([0.2, 0.8])
            with col_clear_btn:
                if st.button("🗑️ Masquer les résultats Podcast", key="btn_clear_pod_results"):
                    st.session_state.podcast_generation_results = None
                    st.rerun()
            st.markdown("---")
        
        # Sélection du carnet
        # Chercher les derniers carnets créés en BDD pour peupler le sélecteur
        notebook_list = []
        if os.path.exists(DB_FILE):
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM notebook ORDER BY id DESC LIMIT 15")
                notebook_list = [row[0] for row in cursor.fetchall()]
                conn.close()
            except:
                pass
                
        # Ajouter le carnet en session state en premier s'il y est
        if st.session_state.current_notebook and st.session_state.current_notebook not in notebook_list:
            notebook_list.insert(0, st.session_state.current_notebook)
            
        if not notebook_list:
            st.info("Aucun carnet n'a été enregistré en base. Créez un carnet à l'étape précédente.")
        else:
            selected_nb_name = st.selectbox(
                "Sélectionnez le carnet de veille à traiter :",
                options=notebook_list,
                index=0
            )
            
            st.markdown("### 🧬 Ingestion Graphe (Neo4j)")
            st.markdown("""
            Cette action va interroger l'API NotebookLM pour générer et télécharger la mindmap sémantique au format JSON,
            puis la traduire en ontologie formelle (nœuds et liens) via Gemini, et enfin l'insérer dans Neo4j.
            """)
            
            if st.button("⚡ Ingestion Complète dans Neo4j (Mindmap + Ingestion)", type="primary", key="btn_neo_ingest"):
                stats_before = get_neo4j_stats()
                nodes_before = stats_before['nodes']
                rels_before = stats_before['relations']
                
                log_placeholder = st.empty()
                stream = StreamToStreamlit(log_placeholder)
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = stream, stream
                
                try:
                    # 1. Generate Mindmap
                    print("\n--- [ÉTAPE 5] RÉCUPÉRATION ET TÉLÉCHARGEMENT MINDMAP JSON ---")
                    json_path = asyncio.run(generate_mindmap.run(selected_nb_name))
                    
                    if json_path:
                        # 2. JSON to Graph
                        print("\n--- [ÉTAPE 6] TRADUCTION DE LA MINDMAP EN GRAPHE SÉMANTIQUE (GEMINI) ---")
                        json_to_graph.run(json_path)
                        
                        # 3. Ingest Neo4j
                        graph_json_path = json_path.replace(".json", "_graph_extracted.json")
                        print("\n--- [ÉTAPE 7] INGESTION DANS LA BASE NEO4J LOCALE ---")
                        neo4j_ingestion.ingest_graph(graph_json_path)
                        print("\n>>> SYNCHRONISATION DU GRAPHE TERMINEE AVEC SUCCES <<<")
                    else:
                        print("\n[ERREUR] Impossible de récupérer la Mindmap depuis NotebookLM.")
                except Exception as e:
                    print(f"\n[ERREUR CRITIQUE] {e}")
                finally:
                    sys.stdout, sys.stderr = old_stdout, old_stderr
                    
                stats_after = get_neo4j_stats()
                new_nodes = stats_after['nodes'] - nodes_before
                new_rels = stats_after['relations'] - rels_before
                
                st.session_state.neo4j_ingestion_results = {
                    'title': f"Ingestion Graphe Neo4j terminée à {datetime.now().strftime('%H:%M:%S')} !",
                    'details': (
                        f"• 🧬 <b>Nouveaux nœuds ajoutés à Neo4j</b> : {new_nodes}<br>"
                        f"• 🔗 <b>Nouvelles relations créées dans Neo4j</b> : {new_rels}"
                    ),
                    'logs': stream.buffer.getvalue()
                }
                st.rerun()
                
            st.markdown("---")
            st.markdown("### 🎙️ Génération Podcast Audio")
            st.markdown("""
            Lance le processus de génération de Podcast Audio de format long (Deep Dive analytique) en français.
            L'opération est asynchrone sur les serveurs de NotebookLM (fire & forget, dure environ 5-10 minutes).
            """)
            
            if st.button("🎙️ Lancer la génération audio du Podcast", key="btn_podcast"):
                log_placeholder = st.empty()
                stream = StreamToStreamlit(log_placeholder)
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = stream, stream
                
                try:
                    asyncio.run(generate_podcast.run(selected_nb_name))
                except Exception as e:
                    print(f"[ERREUR] {e}")
                finally:
                    sys.stdout, sys.stderr = old_stdout, old_stderr
                    
                st.session_state.podcast_generation_results = {
                    'title': f"Génération du Podcast lancée à {datetime.now().strftime('%H:%M:%S')} !",
                    'details': (
                        f"• 🎙️ <b>Génération demandée pour le carnet</b> : {selected_nb_name}<br>"
                        f"• ⏳ <b>Statut de l'audio</b> : En cours de génération asynchrone (5-10 minutes sur NotebookLM)."
                    ),
                    'logs': stream.buffer.getvalue()
                }
                st.rerun()

# ---------------------------------------------------------
# ONGLET 3 : CONFIGURATION & ÉDITEUR
# ---------------------------------------------------------
with tab_config:
    st.markdown("## 🔧 Configuration des Critères & Thèmes")
    st.markdown("Modifiez les règles sémantiques et la taxonomie utilisées par l'IA de tri.")
    
    col_c1, col_c2 = st.columns(2)
    
    # 1. Éditeur de critères (criteria.md)
    with col_c1:
        st.subheader("📋 Critères d'Intérêt (criteria.md)")
        st.caption("Langage naturel utilisé comme instruction système pour rejeter ou accepter les articles.")
        
        criteria_content = ""
        if os.path.exists('criteria.md'):
            with open('criteria.md', 'r', encoding='utf-8') as f:
                criteria_content = f.read()
                
        new_criteria = st.text_area(
            "Rédigez vos critères de filtrage :",
            value=criteria_content,
            height=450,
            key="area_criteria"
        )
        
        if st.button("💾 Sauvegarder les Critères", key="btn_save_crit"):
            try:
                with open('criteria.md', 'w', encoding='utf-8') as f:
                    f.write(new_criteria)
                st.success("Fichier criteria.md enregistré !")
            except Exception as e:
                st.error(f"Erreur d'écriture : {e}")
                
    # 2. Éditeur de thèmes (themes.json)
    with col_c2:
        st.subheader("🏷️ Thématiques Autorisées (themes.json)")
        st.caption("Uniquement ces thèmes seront attribués aux articles par l'IA et utilisés pour la création de carnets.")
        
        themes_list = []
        if os.path.exists('themes.json'):
            with open('themes.json', 'r', encoding='utf-8') as f:
                themes_list = json.load(f)
                
        # Affichage simplifié : un thème par ligne
        themes_string = "\n".join(themes_list)
        new_themes_str = st.text_area(
            "Liste des thèmes (un par ligne) :",
            value=themes_string,
            height=450,
            key="area_themes"
        )
        
        if st.button("💾 Sauvegarder les Thèmes", key="btn_save_themes"):
            try:
                # Convertir le texte en liste
                final_themes = [line.strip() for line in new_themes_str.split("\n") if line.strip()]
                with open('themes.json', 'w', encoding='utf-8') as f:
                    json.dump(final_themes, f, indent=4, ensure_ascii=False)
                st.success("Fichier themes.json mis à jour !")
            except Exception as e:
                st.error(f"Erreur d'écriture : {e}")
