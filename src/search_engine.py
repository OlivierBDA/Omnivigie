import os
from tavily import TavilyClient

def fetch_articles(query, max_results=5, days=15):
    """
    Lance une recherche sur Tavily pour les actualités récentes.
    Retourne une liste de dictionnaires contenant les résultats.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or api_key == "tvly-VOTRE_CLE_API_ICI":
        raise ValueError("Clé API Tavily (TAVILY_API_KEY) manquante ou invalide dans le .env")
        
    tavily = TavilyClient(api_key=api_key)
    
    print(f"Recherche Tavily en cours : '{query}'")
    response = tavily.search(
        query=query,
        search_depth="advanced",
        topic="news",
        days=days,
        include_images=False,
        max_results=max_results
    )
    
    return response.get("results", [])
