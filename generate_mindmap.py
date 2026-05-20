import os
import asyncio
import sqlite3
from notebooklm.client import NotebookLMClient
from notebooklm.types import ArtifactType

DB_FILE = os.path.join('data', 'refined', 'newsletter.db')

async def run(notebook_name):
    print("Connexion à NotebookLM...")
    try:
        async with await NotebookLMClient.from_storage() as client:
            print(f"Recherche du carnet : '{notebook_name}'...")
            notebooks = await client.notebooks.list()
            target_nb = next((nb for nb in notebooks if nb.title == notebook_name), None)
            
            if not target_nb:
                print(f"Erreur : Carnet '{notebook_name}' introuvable.")
                return None
                
            print(f"Carnet trouvé (ID: {target_nb.id}). Lancement de la génération de la mindmap...")
            await client.artifacts.generate_mind_map(
                notebook_id=target_nb.id,
                language="fr"
            )
            print("[OK] Requête de génération de la Mindmap envoyée.")
            
            # Boucle d'attente
            max_retries = 5
            mindmap = None
            for attempt in range(max_retries):
                print(f"Tentative {attempt + 1}/{max_retries} : Recherche de la mindmap...")
                mindmaps = await client.artifacts.list(
                    notebook_id=target_nb.id, 
                    artifact_type=ArtifactType.MIND_MAP
                )
                
                if mindmaps:
                    mindmap = mindmaps[0]
                    break
                    
                print("Mindmap non prête. Attente de 60 secondes...")
                await asyncio.sleep(60)
                
            if not mindmap:
                print("Erreur : La Mindmap n'est toujours pas disponible après plusieurs tentatives.")
                return None
                
            print(f"Mindmap trouvée (ID: {mindmap.id}). Téléchargement en cours...")
            
            output_dir = os.path.join("data", "raw", "notebook", "mindmap")
            os.makedirs(output_dir, exist_ok=True)
            
            safe_name = "".join(c for c in notebook_name if c.isalnum() or c in " -_[]").strip()
            output_path = os.path.join(output_dir, f"{safe_name}.json")
            
            saved_path = await client.artifacts.download_mind_map(
                notebook_id=target_nb.id,
                output_path=output_path,
                artifact_id=mindmap.id
            )
            
            print(f"[OK] Mindmap sauvegardée avec succès dans :\n{saved_path}")
            
            # Mise à jour DB
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            json_filename = f"{safe_name}.json"
            cursor.execute("UPDATE notebook SET mindmap_json = ? WHERE name = ?", (json_filename, notebook_name))
            conn.commit()
            conn.close()
            print("Base de données mise à jour avec le nom du JSON.")
            
            return saved_path
            
    except Exception as e:
        print(f"Erreur lors de la génération/récupération de la Mindmap : {e}")
        return None
