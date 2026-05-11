import asyncio
from notebooklm.client import NotebookLMClient
from notebooklm.rpc import AudioLength, AudioFormat

async def main():
    print("Connexion à NotebookLM...")
    try:
        async with await NotebookLMClient.from_storage() as client:
            # Chercher le carnet [TEST] RAG vision globale
            notebook_name = "[TEST] RAG vision globale"
            notebooks = await client.notebooks.list()
            
            target_nb = None
            for nb in notebooks:
                if nb.title == notebook_name:
                    target_nb = nb
                    break
                    
            if not target_nb:
                print(f"Carnet '{notebook_name}' introuvable.")
                return
                
            print(f"Carnet trouvé (ID: {target_nb.id}). Lancement de la génération audio...")
            
            # Paramétrer la génération courte
            status = await client.artifacts.generate_audio(
                notebook_id=target_nb.id,
                language="fr",
                instructions="Fais un brief rapide du contenu de ces documents. Le format doit être très court et aller droit au but.",
                audio_length=AudioLength.SHORT,
                audio_format=AudioFormat.BRIEF
            )
            
            print(f"Génération lancée avec succès (Task ID: {status.task_id}) !")
            print("L'opération peut prendre quelques minutes.")
            
            # On peut décider de télécharger le fichier ou juste laisser l'UI s'en charger.
            print("Vous pouvez suivre l'avancement directement dans l'interface web de NotebookLM.")
            
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    asyncio.run(main())
