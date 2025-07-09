# backend_scraapy.py (Version finale, avec le sélecteur le plus robuste)

import os
from typing import List, Dict, TypedDict, Optional
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, END
import trafilatura

# --- Configuration ---
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY n'est pas configurée.")
llm = ChatDeepSeek(model="deepseek-chat", temperature=0, max_retries=2)
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGSMITH_TRACING", "true")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT")

# --- Types ---
class FoundArticle(TypedDict):
    title: str; url: str
class ProcessedArticle(FoundArticle):
    content: str; summary: str
class AgentState(TypedDict):
    query: str;sites_to_process: List[str];current_site: str; found_articles: List[FoundArticle]; processed_articles: List[ProcessedArticle]; final_report: Optional[str]; error_message: Optional[str]

# --- Nœuds du Graphe ---

DOMAINES_A_IGNORER = [
    'bloomberg.com',
    'wsj.com',
    'nytimes.com',
    'reuters.com',
    'ft.com',
    'theinformation.com',
    'axios.com',
    't.co', # Liens Twitter
    'ad.doubleclick.net' # Publicité
]

def scrape_techmeme(soup: BeautifulSoup, base_url: str) -> List[FoundArticle]:
    """Scrape les articles de Techmeme en filtrant les sources problématiques."""
    articles = []
    for link in soup.select('strong > a'):
        href, title = link.get('href'), link.get_text(strip=True)
        if href and title:
            # === AJOUT DE LA LOGIQUE DE FILTRAGE ===
            if not any(domaine in href for domaine in DOMAINES_A_IGNORER):
                full_url = urljoin(base_url, href)
                articles.append({"title": title, "url": full_url, "source": "Techmeme"})
            else:
                print(f"  -> Ignoré (source bloquée) : {href}")

    return articles

def scrape_techcabal(soup: BeautifulSoup, base_url: str) -> List[FoundArticle]:
    """Scrape les articles de TechCabal (sélecteur final et correct)."""
    articles = []
    
  
    # On cherche le lien avec la classe 'article-list-title' dans chaque 'article'
    # avec la classe 'article-list-item'. C'est très spécifique et robuste.
    selector = "article.article-list-item a.article-list-title"
    
    for link in soup.select(selector):
        title = link.get_text(strip=True)
        href = link.get('href')
        if title and href:
            # urljoin s'assure que l'URL est complète
            articles.append({"title": title, "url": urljoin(base_url, href), "source": "TechCabal"})
            
    return articles


def scrape_techpoint_africa(soup: BeautifulSoup, base_url: str) -> List[FoundArticle]:
    """Scrape les articles de TechPoint Africa (sélecteur final et correct)."""
    articles = []
    
    # On cible les liens dans les conteneurs d'articles identifiés.
    # C'est un sélecteur très spécifique pour éviter les faux positifs.
    selector = "div.gb-query-loop-item .value a"
    
    for link in soup.select(selector):
        href = link.get('href')
        # .get_text(strip=True) va extraire le texte même s'il y a des balises <font>
        title = link.get_text(strip=True)
        
        if href and title:
            # urljoin s'assure que l'URL est complète
            articles.append({"title": title, "url": urljoin(base_url, href), "source": "TechPoint Africa"})
            
    return articles



def scrape_disruptafrica(soup: BeautifulSoup, base_url: str) -> List[FoundArticle]:
    """Scrape les articles de Disrupt Africa (sélecteur final et correct)."""
    articles = []
    
    # On cherche tous les liens <a> qui sont à l'intérieur d'un élément 
    # (h2, h3, h4...) avec la classe "post-title".
    selector = ".post-title a"
    
    for link in soup.select(selector):
        href = link.get('href')
        # On nettoie le texte, car il peut y avoir des balises <font> à l'intérieur
        title = link.get_text(strip=True)
        
        if href and title:
            # urljoin s'assure que l'URL est complète
            articles.append({"title": title, "url": urljoin(base_url, href), "source": "Disrupt Africa"})
            
    return articles


def scrape_weetracker(soup: BeautifulSoup, base_url: str) -> List[FoundArticle]:
    """Scrape les articles de WeeTracker (sélecteur final et correct)."""
    articles = []
    

    # On cherche tous les liens <a> à l'intérieur d'un h5 avec la classe "f-title".
    selector = "h5.f-title a"
    
    for link in soup.select(selector):
        href = link.get('href')
        title = link.get_text(strip=True)
        
        if href and title:
            # urljoin s'assure que l'URL est complète
            articles.append({"title": title, "url": urljoin(base_url, href), "source": "WeeTracker"})
            
    return articles



SCRAPER_REGISTRY = {
    "https://www.techmeme.com/": scrape_techmeme,
    "https://techcabal.com/": scrape_techcabal,
    "https://techpoint.africa/": scrape_techpoint_africa,
    "https://disruptafrica.com/": scrape_disruptafrica, 
    "https://weetracker.com/": scrape_weetracker,         
}

def plan_next_site(state: AgentState) -> AgentState:
    """Prépare le prochain site à scraper ou termine la boucle."""
    print("--- NŒUD : Planification du prochain site ---")
    sites = state.get("sites_to_process", []).copy()
    if sites:
        next_site = sites.pop(0)
        state["current_site"] = next_site
        state["sites_to_process"] = sites
    else:
        state["current_site"] = "" # Signale la fin de la boucle
    return state

def scraper_dispatcher(state: AgentState) -> AgentState:
    """Appelle le bon scraper pour le site actuel."""
    site_url = state["current_site"]
    print(f"--- NŒUD : Dispatching vers le scraper pour {site_url} ---")
    scraper_function = SCRAPER_REGISTRY.get(site_url)
    
    if not scraper_function:
        print(f"AVERTISSEMENT : Aucun scraper trouvé pour {site_url}. On passe.")
        return state
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0 ...'}
        response = requests.get(site_url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        new_articles = scraper_function(soup, site_url)
        print(f"Trouvé {len(new_articles)} articles sur {site_url}.")
        
        # On ajoute les articles trouvés à la liste existante
        current_articles = state.get("found_articles", [])
        state["found_articles"] = current_articles + new_articles
    except Exception as e:
        print(f"ERREUR lors du scraping de {site_url}: {e}")
        
    return state

def extract_and_summarize(state: AgentState) -> AgentState:
    """
    Prend TOUS les articles trouvés, extrait leur contenu de manière robuste, et génère un rapport.
    """
    print("\n--- NŒUD FINAL : Extraction, Résumé et Rapport (Version Robuste) ---")
    all_found_articles = state.get("found_articles", [])
    if not all_found_articles:
        state["final_report"] = "Aucun article trouvé sur l'ensemble des sites."
        return state

    unique_articles_map = {article['url']: article for article in all_found_articles}
    unique_articles_list = list(unique_articles_map.values())
    print(f"Traitement de {len(unique_articles_list)} articles uniques.")
    
    processed_articles = []
    summary_prompt = ChatPromptTemplate.from_template("Rédige un résumé concis de 2 à 3 phrases pour l'article suivant:\n\nTITRE: {title}\nCONTENU: {content}")
    summary_chain = summary_prompt | llm

    for article in unique_articles_list:
        try:
            # === LA CORRECTION EST ICI ===
            # Étape 1 : Télécharger la page en premier
            downloaded = trafilatura.fetch_url(article['url'])

            # Étape 2 : Vérifier si le téléchargement a réussi AVANT de continuer
            if downloaded:
                content = trafilatura.extract(downloaded, favor_recall=True)
                metadata = trafilatura.extract_metadata(downloaded)
                date = metadata.date if metadata else "N/A"
                summary = ""
                
                if content:
                    response = summary_chain.invoke({"title": article["title"], "content": content[:4000]})
                    summary = response.content
                
                processed_articles.append({**article, "content": content or "", "summary": summary, "date": date})
            else:
                # Si le téléchargement a échoué, on ne fait rien et on logue l'info
                print(f"AVERTISSEMENT : Impossible de télécharger {article['url']}. Article ignoré.")

        except Exception as e:
            # Gérer les autres erreurs de manière gracieuse
            print(f"ERREUR lors du traitement de {article['url']}: {e}. Article ignoré.")
    
    # Construction du rapport final (inchangé)
    report_parts = [f"# Rapport de Veille pour : {state['query']}\n"]
    for article in processed_articles:
        report_parts.append(f"## {article['title']}")
        report_parts.append(f"**Source:** {article['source']} | **Date:** {article.get('date', 'N/A')}")
        report_parts.append(f"**URL:** [{article['url']}]({article['url']})")
        report_parts.append(f"**Résumé:** {article['summary']}\n")
    
    state["final_report"] = "\n".join(report_parts)
    state["processed_articles"] = processed_articles
    return state

# --- Logique de Routage ---
def should_continue(state: AgentState) -> str:
    """Décide s'il faut continuer la boucle de scraping."""
    if state.get("current_site"):
        return "continue_scraping"
    else:
        return "end_scraping"

# --- Construction du Graphe ---
def create_langgraph_app():
    graph = StateGraph(AgentState)
    graph.add_node("planner", plan_next_site)
    graph.add_node("dispatcher", scraper_dispatcher)
    graph.add_node("aggregate_and_report", extract_and_summarize)
    
    graph.set_entry_point("planner")
    
    graph.add_conditional_edges(
        "planner",
        should_continue,
        {"continue_scraping": "dispatcher", "end_scraping": "aggregate_and_report"}
    )
    graph.add_edge("dispatcher", "planner") # La boucle
    graph.add_edge("aggregate_and_report", END)
    
    return graph.compile()

langgraph_app = create_langgraph_app()

# --- Runner ---
async def run_veile_workflow(query: str) -> Dict:
    initial_state = {
        "query": query,
        "sites_to_process": list(SCRAPER_REGISTRY.keys()),
        "found_articles": [],
    }
    try:
        # On remet une limite de récursion car nous avons une boucle
        final_state = await langgraph_app.ainvoke(initial_state, {"recursion_limit": 15})
        return final_state
    except Exception as e:
        return {"error_message": f"Erreur critique du workflow: {e}"}