from notebooklm.rpc import AudioLength, AudioFormat

async def setup_notebook(client, title, urls):
    """
    Crée un nouveau carnet dans NotebookLM et y ajoute les sources (URLs).
    Retourne l'ID du carnet créé.
    """
    print(f"Création du carnet NotebookLM : '{title}'...")
    nb = await client.notebooks.create(title)
    print(f"Carnet créé avec succès (ID: {nb.id}).")
    
    for i, url in enumerate(urls, 1):
        print(f"Ajout de la source {i}/{len(urls)} : {url}...")
        try:
            await client.sources.add_url(nb.id, url)
        except Exception as e:
            print(f" -> Erreur lors de l'ajout de la source {url} : {e}")
            
    return nb.id

async def generate_podcast(client, notebook_id):
    """
    Lance la génération d'un podcast (Audio Overview) pour le carnet spécifié.
    Retourne l'ID de la tâche.
    """
    print("Lancement de la génération du podcast audio...")
    status = await client.artifacts.generate_audio(
        notebook_id=notebook_id,
        language="fr",
        instructions="Fais un brief rapide du contenu de ces documents. Le format doit être très court et aller droit au but.",
        audio_length=AudioLength.SHORT,
        audio_format=AudioFormat.BRIEF
    )
    print(f"Génération audio démarrée (Task ID: {status.task_id}).")
    return status.task_id
