import os
import re
import json
import argparse
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from google import genai
from google.genai import types

# ==============================================================================
# SCHÉMAS PYDANTIC POUR FORCER LA STRUCTURE DE SORTIE DU LLM
# ==============================================================================

class PropertyKV(BaseModel):
    key: str = Field(description="Nom de la propriété")
    value: str = Field(description="Valeur de la propriété")

class OrganizationNode(BaseModel):
    name: str = Field(description="Nom unique de l'organisation")
    type: str = Field(description="Sous-catégorisation (Entreprise, Laboratoire...)")

class ModelNode(BaseModel):
    name: str = Field(description="Nom du modèle IA")
    version: str = Field(description="Version du modèle")

class PersonNode(BaseModel):
    name: str = Field(description="Prénom et nom")
    role: str = Field(description="Rôle de la personne")

class ConceptNode(BaseModel):
    name: str = Field(description="Nom du concept technique ou scientifique")
    domain: str = Field(description="Domaine d'application")

class GeopoliticalEntityNode(BaseModel):
    name: str = Field(description="Pays ou région")

class NewNodeProposed(BaseModel):
    proposed_label: str = Field(description="Le type de noeud proposé qui manque au modèle")
    primary_key: str = Field(description="L'identifiant unique du noeud")
    properties: List[PropertyKV] = Field(default_factory=list, description="Autres propriétés")

class GraphEdge(BaseModel):
    source_label: str = Field(description="Type du noeud de départ (ex: Organization)")
    source_id: str = Field(description="Clé primaire du noeud de départ")
    relation_type: str = Field(description="Type de la relation (ex: DEVELOPS, INVESTS_IN)")
    target_label: str = Field(description="Type du noeud d'arrivée (ex: Model)")
    target_id: str = Field(description="Clé primaire du noeud d'arrivée")
    properties: Optional[List[PropertyKV]] = Field(default=None, description="Propriétés éventuelles (ex: [{'key': 'market_share', 'value': '38%'}])")

class GraphDataExtraction(BaseModel):
    organizations: List[OrganizationNode]
    models: List[ModelNode]
    persons: List[PersonNode]
    concepts: List[ConceptNode]
    geopolitical_entities: List[GeopoliticalEntityNode]
    new_nodes_proposed: List[NewNodeProposed] = Field(description="Noeuds qui ne rentrent dans aucune des catégories ci-dessus")
    edges: List[GraphEdge]

# ==============================================================================
# SCRIPT PRINCIPAL
# ==============================================================================

def run(json_file_path):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Erreur: GEMINI_API_KEY introuvable.")
        return

    # 1. Lecture du Graph Model
    with open("graphModel.txt", "r", encoding="utf-8") as f:
        graph_model = f.read()

    # 2. Lecture de la Mindmap JSON
    if not os.path.exists(json_file_path):
        print(f"Fichier introuvable : {json_file_path}")
        return
        
    with open(json_file_path, "r", encoding="utf-8") as f:
        mindmap_json = f.read()

    print(f"Fichier chargé : {json_file_path}")
    print("Envoi au LLM Gemini pour extraction du graph de connaissance...")

    client = genai.Client(api_key=api_key)
    
    system_instruction = f"""Tu es un ingénieur Data spécialisé en modélisation de graphes (Knowledge Graph).
Ta mission est d'analyser un JSON représentant une Mindmap générée par NotebookLM, et d'en extraire les entités et les relations pour alimenter une base de données orientée graphe (Kùzu).

Voici le modèle de données cible Kùzu que nous utilisons :
{graph_model}

INSTRUCTIONS :
1. Extrait toutes les entités mentionnées dans la Mindmap et associe-les aux Nœuds définis dans le modèle.
2. Déduis les relations entre ces entités en utilisant les REL TABLES définies dans le modèle (ex: DEVELOPS, IMPLEMENTS, SUB_CONCEPT_OF).
3. Si la Mindmap contient des concepts ou relations qui ne rentrent manifestement PAS dans ce modèle, propose-les via le champ `new_nodes_proposed` ou ajoute une relation personnalisée dans `edges`.
4. IMPORTANT : Si tu proposes un nouveau noeud (`new_nodes_proposed`), tu DOIS obligatoirement proposer au moins une relation (`edges`) qui relie ce nouveau noeud au reste du graphe (soit vers un noeud existant, soit vers un autre nouveau noeud). Un noeud ne doit jamais être orphelin.
5. Reste extrêmement factuel.
"""

    prompt = f"Voici la Mindmap (au format JSON) à analyser et à convertir :\n\n{mindmap_json}"

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=GraphDataExtraction,
                temperature=0.1, # Température basse pour une extraction déterministe
            ),
        )
        
        print("\n[OK] Extraction réussie ! Voici le résultat brut structuré :\n")
        
        # Le retour est déjà formaté en JSON selon notre schéma
        result_data = json.loads(response.text)
        
        # --- TRAITEMENT POST-LLM : AJOUT DU NOEUD DOCUMENT ET MENTIONED_IN ---
        filename = os.path.basename(json_file_path)
        
        import sqlite3
        DB_FILE = os.path.join('data', 'refined', 'newsletter.db')
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at FROM notebook WHERE mindmap_json = ?", (filename,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            doc_id = f"NB-{row[0]}" # ID technique préfixé pour le Graph
            doc_title = row[1]
            doc_date = row[2].split(" ")[0] if row[2] else "1970-01-01"
        else:
            print(f"Avertissement : Le fichier {filename} n'est pas référencé dans la table 'notebook'.")
            doc_id = f"UNKNOWN-{filename}"
            doc_title = filename.replace(".json", "")
            doc_date = "1970-01-01"
            
        # 1. Ajout du noeud Document
        result_data["document"] = {
            "id": doc_id,
            "title": doc_title,
            "publish_date": doc_date
        }
        
        # 2. Ajout des relations MENTIONED_IN
        # Table de correspondance entre la clé de la liste et le nom du label Kùzu
        entity_lists = {
            "organizations": ("Organization", "name"),
            "models": ("Model", "name"),
            "persons": ("Person", "name"),
            "concepts": ("Concept", "name"),
            "geopolitical_entities": ("GeopoliticalEntity", "name"),
            "new_nodes_proposed": (None, "primary_key") # Le label est dynamique
        }
        
        for list_key, (default_label, id_field) in entity_lists.items():
            for entity in result_data.get(list_key, []):
                label = entity.get("proposed_label", default_label) if not default_label else default_label
                entity_id = entity.get(id_field)
                
                if entity_id:
                    result_data["edges"].append({
                        "source_label": label,
                        "source_id": entity_id,
                        "relation_type": "MENTIONED_IN",
                        "target_label": "Document",
                        "target_id": doc_id,
                        "properties": []
                    })
        # ----------------------------------------------------------------------

        print(json.dumps(result_data, indent=2, ensure_ascii=False))
        
        output_test_file = json_file_path.replace(".json", "_graph_extracted.json")
        with open(output_test_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
            
        print(f"\nRésultat sauvegardé dans : {output_test_file}")

    except Exception as e:
        print(f"Erreur lors de l'appel à Gemini : {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tester la transformation d'une Mindmap JSON vers un modèle Kùzu.")
    parser.add_argument("json_file", help="Chemin vers le fichier JSON de la mindmap")
    args = parser.parse_args()
    
    run(args.json_file)
