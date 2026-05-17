import asyncio
import argparse
from notebooklm.client import NotebookLMClient
from notebooklm.rpc import AudioLength, AudioFormat

async def run(notebook_name):
    print("Connexion à NotebookLM...")
    
    try:
        async with await NotebookLMClient.from_storage() as client:
            print(f"Recherche du carnet : '{notebook_name}'...")
            notebooks = await client.notebooks.list()
            
            target_nb = None
            for nb in notebooks:
                if nb.title == notebook_name:
                    target_nb = nb
                    break
                    
            if not target_nb:
                print(f"Erreur : Carnet '{notebook_name}' introuvable.")
                print("Carnets disponibles :")
                for nb in notebooks[:5]:
                    print(f" - {nb.title}")
                return
                
            print(f"Carnet trouvé (ID: {target_nb.id}). Lancement de la génération audio LONGUE...")
            
            # Paramétrer la génération longue
            status = await client.artifacts.generate_audio(
                notebook_id=target_nb.id,
                language="fr",
                instructions="Fais une analyse approfondie et détaillée de ces documents. Prends le temps d'expliquer les concepts clés, les enjeux technologiques et les impacts. Le ton doit être professionnel, captivant et analytique. L'audio est destiné à être écouté par des ingénieurs et des architects data / IA.",
                audio_length=AudioLength.LONG,
                audio_format=AudioFormat.DEEP_DIVE # Utilisation d'un format approfondi (si supporté par l'API communautaire, sinon fallback sur la longueur)
            )
            
            print(f"Génération lancée avec succès (Task ID: {status.task_id}) !")
            print("L'opération est longue et peut prendre jusqu'à 5-10 minutes.")
            print("Vous pouvez suivre l'avancement directement dans l'interface web de NotebookLM, et vous recevrez une notification une fois terminé.")
            
    except Exception as e:
        print(f"Erreur de connexion ou de génération avec l'API NotebookLM : {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Générer un podcast long pour un carnet NotebookLM existant.")
    parser.add_argument("notebook_name", help="Le nom exact du carnet (ex: '[AI] 2026-05-15 TLDR')")
    args = parser.parse_args()
    asyncio.run(run(args.notebook_name))
