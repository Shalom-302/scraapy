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
        impact_afrique: str = Field(description="L'impact direct ou indirect de cet événement sur l'Afrique.")
        problematique_africaine: str = Field(description="La problématique de fond que cela révèle pour le continent.")
        eveil_de_conscience: str = Field(description="La leçon critique, le 'wake-up call' pour l'Afrique.")
        piste_opportunite: str = Field(description="Une idée d'opportunité concrète pour l'écosystème tech africain.")
        type_evenement: str = Field(description="Ex: 'Faillite', 'Lancement de produit', 'Tendance'")
        resume_strategique: str = Field(description="Résumé de l'événement et son importance.")
        lecon_a_retenir: str = Field(description="Le conseil principal à tirer de cet événement.")
        impact_potentiel: str = Field(description="L'impact potentiel sur l'industrie.")
        score_pertinence: int = Field(description="Un score de 1 à 10 indiquant l'importance de cet éveil de conscience pour l'Afrique. 10 est critique.", ge=1, le=10)
        resume_neutre: str = Field(description="Un résumé factuel et dense de l'article, de style journalistique (type agence de presse), ""strictement compris entre 700 et 800 caractères.")
        problematique_generale: str = Field(description="La problématique principale ou universelle soulevée par l'article.")

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
    score_pertinence: Optional[int]
    resume_neutre: Optional[str] 
    problematique_generale: Optional[str]

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

# --- Logique de Routage ---
def should_continue(state: AgentState) -> str:
    return "continue_scraping" if state.get("current_site") else "end_scraping"



# Remplacez votre fonction extract_analyze_and_report par celle-ci
# --- VERSION FINALE AVEC CLASSEMENT COMPLET ---
# Remplacez votre fonction extract_analyze_and_report par celle-ci
# Remplacez votre fonction extract_analyze_and_report par cette version finale et complète

def extract_analyze_and_report(state: AgentState) -> dict:
    print("\n--- NŒUD FINAL : Extraction, Analyse et Rapport ---")
    all_found_articles = state.get("found_articles", [])
    if not all_found_articles:
        return {"final_report": "Aucun article trouvé.", "analyzed_articles": []}

    unique_articles_list = list({article['url']: article for article in all_found_articles}.values())
    print(f"Traitement de {len(unique_articles_list)} articles uniques.")
    
    # NOUVEAU PROMPT COMPLET
    analysis_prompt_template = """Vous êtes un analyste technologique mondial doublé d'un stratège pour l'Afrique. Pour l'article fourni, effectuez une analyse en deux temps :
    
    **Partie 1 : Analyse Globale (Neutre)**
    1.  **Résumé Neutre :** Fournissez un résumé factuel et dense de l'article, de style journalistique (type agence de presse), strictement compris entre 700 et 800 caractères.
    2.  **Problématique Générale :** Identifiez la problématique principale ou universelle soulevée.
    
    **Partie 2 : Analyse Stratégique pour l'Afrique**
    3.  **Impact sur l'Afrique :** Quel est l'impact direct ou indirect pour le continent ?
    4.  **Problématique Spécifique à l'Afrique :** Quelle dépendance ou faiblesse cela révèle-t-il pour l'Afrique ?
    5.  **Éveil de Conscience :** Quelle est la leçon critique pour les acteurs de la tech africaine ?
    6.  **Piste d'Opportunité :** Quelle opportunité concrète cela crée-t-il ?
    7.  **Score de Pertinence :** Attribuez un score de 1 à 10 sur l'importance de cette nouvelle pour l'Afrique.

    Article à analyser : <article_text>{content}</article_text>"""
    
    analysis_prompt = ChatPromptTemplate.from_template(analysis_prompt_template)
    analysis_chain = analysis_prompt | llm.with_structured_output(ArticleAnalysis)

    all_analyzed_articles: List[AnalyzedArticle] = []
    for article in unique_articles_list:
        # Template d'erreur mis à jour avec les nouveaux champs
        base_article_data: AnalyzedArticle = {**article, "content": None, "date": None, "resume_neutre": None, "problematique_generale": None, "impact_afrique": None, "problematique_africaine": None, "eveil_de_conscience": None, "piste_opportunite": None, "score_pertinence": None, "error": None}
        try:
            downloaded = trafilatura.fetch_url(article['url'])
            if not downloaded:
                base_article_data["error"] = "Téléchargement échoué"
                all_analyzed_articles.append(base_article_data); continue
            
            content = trafilatura.extract(downloaded, favor_recall=True)
            date = trafilatura.extract_metadata(downloaded).date if trafilatura.extract_metadata(downloaded) else "N/A"
            
            if content and len(content) > 250:
                try:
                    analysis_result_object = analysis_chain.invoke({"content": content[:8000]})
                    analysis_result_dict = analysis_result_object.dict()
                    full_article: AnalyzedArticle = {**base_article_data, "content": content, "date": date, **analysis_result_dict, "error": None}
                    all_analyzed_articles.append(full_article)
                except Exception as llm_error:
                    base_article_data.update({"content": content, "date": date, "error": f"Erreur du LLM: {llm_error}"})
                    all_analyzed_articles.append(base_article_data)
            else:
                base_article_data.update({"content": content, "date": date, "error": "Contenu insuffisant"})
                all_analyzed_articles.append(base_article_data)
        except Exception as e:
            base_article_data["error"] = f"Erreur d'extraction: {e}"
            all_analyzed_articles.append(base_article_data)

    # Le tri reste le même
    articles_with_score = [article for article in all_analyzed_articles if not article.get("error")]
    articles_with_score.sort(key=lambda x: x.get("score_pertinence", 0), reverse=True)
    print(f"Classement de {len(articles_with_score)} articles analysés par score de pertinence.")

    # NOUVELLE CONSTRUCTION DU RAPPORT ENRICHI
    if not articles_with_score:
        final_report = "# Rapport de Veille Stratégique pour l'Afrique\n\nAucun article n'a pu être analysé avec succès."
    else:
        report_parts = [f"# Rapport de Veille Stratégique pour l'Afrique : {state['query']}\n"]
        for article in articles_with_score:
            score = article.get('score_pertinence')
            score_emoji = "🔥" * (score // 2) + "⚫️" * ((10 - score) // 2) if score else "N/A"

            report_parts.append(f"--- \n\n## {article['title']}")
            report_parts.append(f"**Source:** {article.get('source', 'N/A')} | **Date:** {article.get('date', 'N/A')}")
            
            # --- Partie 1: Contexte Global ---
            report_parts.append(f"\n### Contexte Global")
            report_parts.append(f"**📝 Résumé :** {article.get('resume_neutre', 'N/A')}")
            report_parts.append(f"**🌐 Problématique Générale :** {article.get('problematique_generale', 'N/A')}")

            # --- Partie 2: Analyse pour l'Afrique ---
            report_parts.append(f"\n### Analyse Stratégique pour l'Afrique")
            report_parts.append(f"**Score de Pertinence : {score}/10** {score_emoji}")
            report_parts.append(f"**🌍 Impact :** {article.get('impact_afrique', 'N/A')}")
            report_parts.append(f"**🤔 Problématique Révélée :** {article.get('problematique_africaine', 'N/A')}")
            report_parts.append(f"> **💡 Éveil de Conscience :** {article.get('eveil_de_conscience', 'N/A')}")
            report_parts.append(f"**🚀 Piste d'Opportunité :** {article.get('piste_opportunite', 'N/A')}")
            
            report_parts.append(f"\n_[Lien vers l'article]({article['url']})_")
        final_report = "\n\n".join(report_parts)

    return {"final_report": final_report, "analyzed_articles": all_analyzed_articles}
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