import os
import json
import sqlite3
import re
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List

from google import genai
from google.genai import types

DB_FILE = os.path.join('data', 'refined', 'newsletter.db')
CONFIG_FILE = 'llm_config.json'
CRITERIA_FILE = 'criteria.md'

class ArticleEvaluation(BaseModel):
    id: int
    tags: List[str]
    is_interesting: bool
    explanation: str

class BatchEvaluation(BaseModel):
    evaluations: List[ArticleEvaluation]

def migrate_db():
    """Ajoute les colonnes de qualification si elles n'existent pas."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(tldr_ai)").fetchall()]
    
    if 'tags' not in columns:
        cursor.execute("ALTER TABLE tldr_ai ADD COLUMN tags TEXT")
    if 'is_interesting' not in columns:
        cursor.execute("ALTER TABLE tldr_ai ADD COLUMN is_interesting BOOLEAN")
    if 'explanation' not in columns:
        cursor.execute("ALTER TABLE tldr_ai ADD COLUMN explanation TEXT")
        
    conn.commit()
    conn.close()

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_criteria():
    with open(CRITERIA_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def extract_minutes(time_str):
    if not time_str:
        return None
    match = re.search(r'(\d+)', time_str)
    if match:
        return int(match.group(1))
    return None

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Erreur: GEMINI_API_KEY introuvable dans le fichier .env")
        return

    print("Vérification et migration de la base de données...")
    migrate_db()
    
    config = load_config()
    criteria = load_criteria()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Récupérer les articles non qualifiés
    cursor.execute("SELECT id, title, summary, reading_time, is_sponsor FROM tldr_ai WHERE is_interesting IS NULL")
    articles = cursor.fetchall()
    
    if not articles:
        print("Aucun nouvel article à qualifier.")
        conn.close()
        return
        
    print(f"{len(articles)} articles à analyser.")
    
    # 1. Hard Filter (Sponsor et temps de lecture)
    to_evaluate = []
    hard_filtered_count = 0
    
    for row in articles:
        art_id, title, summary, reading_time, is_sponsor = row
        minutes = extract_minutes(reading_time)
        
        if is_sponsor:
            cursor.execute("UPDATE tldr_ai SET is_interesting=0, explanation=? WHERE id=?", 
                           ("Filtré: Article sponsorisé.", art_id))
            hard_filtered_count += 1
            continue
            
        if minutes is None or minutes < 5:
            cursor.execute("UPDATE tldr_ai SET is_interesting=0, explanation=? WHERE id=?", 
                           (f"Filtré: Temps de lecture insuffisant ({reading_time}).", art_id))
            hard_filtered_count += 1
            continue
            
        # Garder pour l'évaluation LLM
        to_evaluate.append({
            "id": art_id,
            "title": title,
            "summary": summary
        })
        
    conn.commit()
    print(f" -> {hard_filtered_count} articles filtrés par les règles métier (sponsors, temps < 5m).")
    
    if not to_evaluate:
        print("Il ne reste aucun article à évaluer par le LLM.")
        conn.close()
        return
        
    print(f" -> {len(to_evaluate)} articles envoyés à Gemini pour qualification sémantique...")
    
    # 2. Qualification via LLM
    client = genai.Client(api_key=api_key)
    
    prompt = "Voici une liste d'articles (ID, Titre, Résumé). Évalue l'intérêt de CHAQUE article en fonction de mes critères."
    
    try:
        response = client.models.generate_content(
            model=config.get("model_name", "gemini-3.1-flash-lite"),
            contents=[prompt, json.dumps(to_evaluate, ensure_ascii=False)],
            config=types.GenerateContentConfig(
                system_instruction=criteria,
                response_mime_type="application/json",
                response_schema=BatchEvaluation,
                temperature=config.get("temperature", 0.2),
            ),
        )
        
        # 3. Traitement de la réponse et Update BDD
        result_json = json.loads(response.text)
        evaluations = result_json.get("evaluations", [])
        
        interesting_count = 0
        for eval_item in evaluations:
            art_id = eval_item['id']
            tags_str = ", ".join(eval_item['tags'])
            is_int = 1 if eval_item['is_interesting'] else 0
            explanation = eval_item['explanation']
            
            cursor.execute("""
                UPDATE tldr_ai 
                SET tags=?, is_interesting=?, explanation=? 
                WHERE id=?
            """, (tags_str, is_int, explanation, art_id))
            
            if is_int:
                interesting_count += 1
                
        conn.commit()
        print(f"\n✅ Qualification terminée !")
        print(f" -> {interesting_count} articles jugés pertinents par l'IA.")
        print(f" -> {len(evaluations) - interesting_count} articles rejetés par l'IA.")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'appel à Gemini : {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
