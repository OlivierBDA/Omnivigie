import os
from dotenv import load_dotenv
from tavily import TavilyClient

def main():
    # Charge les variables d'environnement depuis .env
    load_dotenv()
    
    # Récupérer la clé API
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or api_key == "tvly-VOTRE_CLE_API_ICI":
        print("❌ ERREUR: Clé API Tavily introuvable.")
        print("Veuillez créer un fichier .env (en vous basant sur .env.example)")
        print("et y insérer votre clé TAVILY_API_KEY=tvly-...")
        return
        
    print("Initialisation du client Tavily...")
    tavily = TavilyClient(api_key=api_key)
    
    query = (
        "Nouvelles informations sur l'intelligence artificielle. "
        "Articles de blog, solutions éditeurs, papiers de recherches, "
        "vidéos Youtube, posts de réseaux sociaux."
    )
    
    print(f"\nLancement de la recherche :\n'{query}'\n")
    print("Recherche en cours (sur les 15 derniers jours)...")
    
    try:
        # L'API Tavily permet d'utiliser topic="news" avec le paramètre "days" 
        # pour restreindre la recherche aux actualités des X derniers jours.
        # search_depth="advanced" permet d'obtenir des résultats de meilleure qualité.
        response = tavily.search(
            query=query,
            search_depth="advanced",
            topic="news",
            days=15,
            include_images=False
        )
        
        results = response.get("results", [])
        print(f"\n✅ {len(results)} résultats trouvés !\n")
        
        print("-" * 50)
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Sans titre')
            url = result.get('url', 'Pas d\'URL')
            score = result.get('score', 0)
            published_date = result.get('published_date', 'Date inconnue')
            
            print(f"Source {i} (Score de pertinence : {score:.2f})")
            print(f"Date : {published_date}")
            print(f"Titre : {title}")
            print(f"URL : {url}")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Erreur lors de la recherche : {e}")

if __name__ == "__main__":
    main()
