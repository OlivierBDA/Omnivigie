import asyncio
import re
import docx
from notebooklm import NotebookLMClient

async def main():
    # 1. Extraire les URLs du fichier docx
    print("Lecture du fichier .docx...")
    doc = docx.Document('catalog/TEST-liste_sources.docx')
    full_text = '\n'.join([p.text for p in doc.paragraphs])
    
    # Expression régulière pour trouver les URLs
    url_pattern = re.compile(r'url:\s*"(https?://[^"]+)"')
    urls = url_pattern.findall(full_text)
    
    if not urls:
        print("Aucune URL trouvée dans le fichier.")
        return

    print(f"{len(urls)} sources trouvées :")
    for url in urls:
        print(f" - {url}")
        
    print("\nConnexion à NotebookLM...")
    try:
        async with await NotebookLMClient.from_storage() as client:
            notebook_name = "[TEST] RAG vision globale"
            print(f"Création du carnet : '{notebook_name}'...")
            
            # Créer le nouveau carnet
            nb = await client.notebooks.create(notebook_name)
            print(f"Carnet créé avec succès (ID: {nb.id}) !")
            
            # Ajouter chaque source au carnet
            for i, url in enumerate(urls, 1):
                print(f"Ajout de la source {i}/{len(urls)} : {url} ...")
                try:
                    await client.sources.add_url(nb.id, url)
                    print(f" -> Source {i} ajoutée.")
                except Exception as e:
                    print(f" -> Erreur lors de l'ajout de la source {i} : {e}")
                    
            print("\nTerminé ! Vous pouvez vérifier votre espace NotebookLM dans le navigateur.")
            
    except Exception as e:
        print(f"Erreur de connexion avec NotebookLM : {e}")

if __name__ == "__main__":
    asyncio.run(main())
