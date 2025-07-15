import os
from typing import List, Dict, TypedDict, Optional
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import trafilatura

from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, END
from pydantic import BaseModel,Field

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


class ArticleAnalysis(BaseModel):
        type_evenement: str = Field(description="Ex: 'Faillite', 'Lancement de produit', 'Tendance'")
        resume_strategique: str = Field(description="Résumé de l'événement et son importance.")
        lecon_a_retenir: str = Field(description="Le conseil principal à tirer de cet événement.")
        impact_potentiel: str = Field(description="L'impact potentiel sur l'industrie.")


# --- SECTION TYPES (Cohérente et Finale) ---
class FoundArticle(TypedDict):
    title: str
    url: str
    source: str

class AnalyzedArticle(FoundArticle):
    content: Optional[str]
    date: Optional[str]
    type_evenement: Optional[str]
    resume_strategique: Optional[str]
    lecon_a_retenir: Optional[str]
    impact_potentiel: Optional[str]
    error: Optional[str]

class AgentState(TypedDict):
    query: str
    sites_to_process: List[str]
    current_site: str
    found_articles: List[FoundArticle]
    analyzed_articles: List[AnalyzedArticle]
    final_report: Optional[str]
    error_message: Optional[str]


# --- Fonctions de Scraping ---
DOMAINES_A_IGNORER = ['bloomberg.com', 'wsj.com', 'nytimes.com', 'reuters.com', 'ft.com', 'theinformation.com', 'axios.com', 't.co', 'ad.doubleclick.net']
def scrape_techmeme(soup: BeautifulSoup, base_url: str) -> List[FoundArticle]:
    articles = []
    for link in soup.select('strong > a'):
        href, title = link.get('href'), link.get_text(strip=True)
        if href and title and not any(domaine in href for domaine in DOMAINES_A_IGNORER):
            articles.append({"title": title, "url": urljoin(base_url, href), "source": "Techmeme"})
    return articles
def scrape_techcabal(soup: BeautifulSoup, base_url: str) -> List[FoundArticle]:
    articles = []
    for link in soup.select("article.article-list-item a.article-list-title"):
        title, href = link.get_text(strip=True), link.get('href')
        if title and href: articles.append({"title": title, "url": urljoin(base_url, href), "source": "TechCabal"})
    return articles
def scrape_techpoint_africa(soup: BeautifulSoup, base_url: str) -> List[FoundArticle]:
    articles = []
    for link in soup.select("div.gb-query-loop-item .value a"):
        href, title = link.get_text(strip=True), link.get('href')
        if href and title: articles.append({"title": title, "url": urljoin(base_url, href), "source": "TechPoint Africa"})
    return articles
def scrape_disruptafrica(soup: BeautifulSoup, base_url: str) -> List[FoundArticle]:
    articles = []
    for link in soup.select(".post-title a"):
        href, title = link.get_text(strip=True), link.get('href')
        if href and title: articles.append({"title": title, "url": urljoin(base_url, href), "source": "Disrupt Africa"})
    return articles
def scrape_weetracker(soup: BeautifulSoup, base_url: str) -> List[FoundArticle]:
    articles = []
    for link in soup.select("h5.f-title a"):
        href, title = link.get_text(strip=True), link.get('href')
        if href and title: articles.append({"title": title, "url": urljoin(base_url, href), "source": "WeeTracker"})
    return articles
SCRAPER_REGISTRY = {
    "https://www.techmeme.com/": scrape_techmeme, "https://techcabal.com/": scrape_techcabal,
    "https://techpoint.africa/": scrape_techpoint_africa, "https://disruptafrica.com/": scrape_disruptafrica, 
    "https://weetracker.com/": scrape_weetracker,         
}


# --- NOEUDS DU GRAPHE ---
def plan_next_site(state: AgentState) -> dict:
    print("--- NŒUD : Planification du prochain site ---")
    sites = state.get("sites_to_process", []).copy()
    if sites:
        next_site = sites.pop(0)
        return {"current_site": next_site, "sites_to_process": sites}
    else:
        return {"current_site": ""}

def scraper_dispatcher(state: AgentState) -> dict:
    site_url = state["current_site"]
    print(f"--- NŒUD : Dispatching vers le scraper pour {site_url} ---")
    scraper_function = SCRAPER_REGISTRY.get(site_url)
    if not scraper_function: return {}
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(site_url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        new_articles = scraper_function(soup, site_url)
        print(f"Trouvé {len(new_articles)} articles sur {site_url}.")
        current_articles = state.get("found_articles", [])
        return {"found_articles": current_articles + new_articles}
    except Exception as e:
        print(f"ERREUR lors du scraping de {site_url}: {e}")
        return {}




def extract_analyze_and_report(state: AgentState) -> dict:
    """
    NŒUD FINAL : Prend les articles trouvés, extrait leur contenu, les analyse via un LLM
    avec une structure Pydantic, filtre les résultats pertinents et génère un rapport final.
    """
    print("\n--- NŒUD FINAL : Extraction, Analyse et Rapport ---")
    
    # Récupération et dédoublonnage des articles
    all_found_articles = state.get("found_articles", [])
    if not all_found_articles:
        return {"final_report": "Aucun article trouvé à traiter.", "analyzed_articles": []}

    unique_articles_list = list({article['url']: article for article in all_found_articles}.values())
    print(f"Traitement de {len(unique_articles_list)} articles uniques.")
    
    # Création de la chaîne d'analyse LangChain.
    # Elle utilise le modèle Pydantic `ArticleAnalysis` défini au niveau du module.
    analysis_prompt_template = """Vous êtes un analyste technologique et stratégique. Lisez l'article suivant et extrayez la "leçon de conscience".
    Analysez le texte : <article_text>{content}</article_text>"""
    analysis_prompt = ChatPromptTemplate.from_template(analysis_prompt_template)
    analysis_chain = analysis_prompt | llm.with_structured_output(ArticleAnalysis)

    # Liste pour stocker tous les articles après traitement (succès ou échec)
    all_analyzed_articles: List[AnalyzedArticle] = []
    
    # Boucle de traitement pour chaque article unique
    for article in unique_articles_list:
        # Création d'un "template" d'article en cas d'erreur pour garantir la cohérence des types.
        # Toutes les clés de `AnalyzedArticle` sont présentes et initialisées à None.
        base_article_data: AnalyzedArticle = {
            **article, "content": None, "date": None, "type_evenement": None,
            "resume_strategique": None, "lecon_a_retenir": None, "impact_potentiel": None, "error": None
        }
        
        try:
            # 1. Téléchargement et extraction du contenu
            downloaded = trafilatura.fetch_url(article['url'])
            if not downloaded:
                base_article_data["error"] = "Téléchargement échoué"
                all_analyzed_articles.append(base_article_data)
                continue # Passe à l'article suivant
            
            content = trafilatura.extract(downloaded, favor_recall=True)
            metadata = trafilatura.extract_metadata(downloaded)
            date = metadata.date if metadata else "N/A"
            
            # 2. Vérification et analyse par le LLM
            if content and len(content) > 250:
                try:
                    # Invocation de la chaîne, qui retourne un objet Pydantic
                    analysis_result_object = analysis_chain.invoke({"content": content[:8000]})
                    
                    # Conversion de l'objet Pydantic en dictionnaire Python
                    analysis_result_dict = analysis_result_object.dict()
                    
                    # Création de l'objet final complet et bien typé
                    full_article: AnalyzedArticle = {
                        **base_article_data, 
                        "content": content, 
                        "date": date, 
                        **analysis_result_dict, 
                        "error": None
                    }
                    all_analyzed_articles.append(full_article)
                    
                except Exception as llm_error:
                    # En cas d'échec du LLM, on stocke l'erreur
                    base_article_data.update({"content": content, "date": date, "error": f"Erreur du LLM: {llm_error}"})
                    all_analyzed_articles.append(base_article_data)
            else:
                # Si le contenu est insuffisant
                base_article_data.update({"content": content, "date": date, "error": "Contenu insuffisant"})
                all_analyzed_articles.append(base_article_data)
                
        except Exception as e:
            # En cas d'échec de l'extraction
            base_article_data["error"] = f"Erreur d'extraction: {e}"
            all_analyzed_articles.append(base_article_data)

    # Filtrage des articles pour ne garder que les plus pertinents pour le rapport
    print(f"Filtrage des {len(all_analyzed_articles)} articles pour le rapport final...")
    insightful_articles = [
        article for article in all_analyzed_articles 
        if not article.get("error") and article.get("lecon_a_retenir")
    ]
    print(f"Trouvé {len(insightful_articles)} articles avec une leçon de conscience pertinente.")

    # Construction du rapport final à partir des articles filtrés
    if not insightful_articles:
        final_report = "# Rapport de Veille\n\nAucun article avec une leçon de conscience claire n'a été trouvé après analyse."
    else:
        report_parts = [f"# Rapport de Veille Stratégique : {state['query']}\n"]
        for article in insightful_articles:
            report_parts.append(f"## {article['title']}")
            report_parts.append(f"**Source:** {article.get('source', 'N/A')} | **Date:** {article.get('date', 'N/A')}")
            report_parts.append(f"**Analyse :** {article.get('resume_strategique', 'N/A')}")
            report_parts.append(f"> **💡 Leçon à retenir :** {article.get('lecon_a_retenir', 'N/A')}\n")
            report_parts.append(f"_[Lien vers l'article]({article['url']})_")
        final_report = "\n\n".join(report_parts)

    # La fonction retourne un dictionnaire contenant les clés à mettre à jour dans l'état
    return {
        "final_report": final_report,
        "analyzed_articles": all_analyzed_articles # On retourne tous les articles pour un éventuel affichage détaillé
    }

# --- Logique de Routage ---
def should_continue(state: AgentState) -> str:
    return "continue_scraping" if state.get("current_site") else "end_scraping"


# --- Construction du Graphe ---
def create_langgraph_app():
    graph = StateGraph(AgentState)
    graph.add_node("planner", plan_next_site)
    graph.add_node("dispatcher", scraper_dispatcher)
    graph.add_node("aggregate_and_report", extract_analyze_and_report)
    graph.set_entry_point("planner")
    graph.add_conditional_edges("planner", should_continue, {"continue_scraping": "dispatcher", "end_scraping": "aggregate_and_report"})
    graph.add_edge("dispatcher", "planner")
    graph.add_edge("aggregate_and_report", END)
    return graph.compile()

langgraph_app = create_langgraph_app()


# --- Runner ---
async def run_veile_workflow(query: str) -> Dict:
    initial_state = {
        "query": query, "sites_to_process": list(SCRAPER_REGISTRY.keys()),
        "found_articles": [], "analyzed_articles": [], "final_report": "", "error_message": None
    }
    try:
        final_state = await langgraph_app.ainvoke(initial_state, {"recursion_limit": 15})
        return {
            "final_report": final_state.get("final_report"),
            "analyzed_articles": final_state.get("analyzed_articles"),
            "error_message": final_state.get("error_message")
        }
    except Exception as e:
        print(f"ERREUR CRITIQUE DANS LE WORKFLOW: {e}")
        return {"error_message": f"Erreur critique du workflow: {e}"}