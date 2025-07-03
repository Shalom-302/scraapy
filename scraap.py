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
    query: str; found_articles: List[FoundArticle]; processed_articles: List[ProcessedArticle]; final_report: Optional[str]; error_message: Optional[str]

# --- Nœuds du Graphe ---

def scrape_techmeme_homepage(state: AgentState) -> AgentState:
    print("--- NŒUD 1 : Scraping de Techmeme avec le sélecteur final ---")
    target_url = "https://www.techmeme.com/"
    articles_found = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # =========================================================================
        # === LE SÉLECTEUR FINAL, LE PLUS SIMPLE ET LE PLUS FONDAMENTAL        ===
        # === Tous les titres d'articles sont des liens dans une balise <strong>    ===
        # =========================================================================
        selector = 'strong > a'
        article_links = soup.select(selector)
        
        print(f"DIAGNOSTIC : {len(article_links)} articles trouvés avec le sélecteur final ('{selector}').")

        if not article_links:
            state["error_message"] = "Le sélecteur 'strong > a' n'a retourné aucun article. La structure de Techmeme a radicalement changé."
            return state

        for link in article_links:
            href = link.get('href')
            title = link.get_text(strip=True)
            if href and not href.startswith('http'):
                href = urljoin(target_url, href)
            if href and title:
                articles_found.append({"title": title, "url": href})
        
        # Pour éviter les doublons, car plusieurs liens peuvent pointer vers le même article
        unique_articles = list({article['url']: article for article in articles_found}.values())
        print(f"Trouvé {len(unique_articles)} articles uniques.")
        state["found_articles"] = unique_articles
        return state

    except Exception as e:
        state["error_message"] = f"Erreur critique lors du scraping : {e}"
        return state

def extract_full_content(state: AgentState) -> AgentState:
    """
    Prend la liste d'articles, visite chaque URL, et extrait le contenu ET la date.
    """
    print("--- NŒUD 2 : Extraction du contenu et de la date des articles ---")
    articles_to_process = state.get("found_articles", [])
    processed_articles = []
    
    if not articles_to_process:
        print("Aucun article trouvé à l'étape précédente.")
        state["processed_articles"] = []
        return state

    for article in articles_to_process:
        try:
            print(f"Extraction de : {article['url']}")
            downloaded = trafilatura.fetch_url(article['url'])
            
            # Extraire le contenu
            content = trafilatura.extract(downloaded, favor_recall=True) if downloaded else ""
            
            # Extraire les métadonnées, y compris la date
            metadata = trafilatura.extract_metadata(downloaded)
            date = metadata.date if metadata else "Date non trouvée"
            
            if content:
                processed_articles.append({
                    "title": article["title"],
                    "url": article["url"],
                    "content": content,
                    "date": date, # On utilise la date extraite
                    "summary": ""
                })
        except Exception as e:
            print(f"Erreur d'extraction pour {article['url']}: {e}")
            
    state["processed_articles"] = processed_articles
    return state

def summarize_and_report(state: AgentState) -> AgentState:
    """
    Parcourt les articles avec leur contenu complet, génère un résumé pour chacun,
    et compile tout dans un rapport final en Markdown, en incluant la date.
    """
    print("--- NŒUD 3 : Résumé et génération du rapport ---")
    articles_with_content = state.get("processed_articles", [])
    
    if not articles_with_content:
        state["final_report"] = "Aucun article n'a pu être traité pour générer un rapport."
        return state

    summary_prompt = ChatPromptTemplate.from_template(
        "Rédige un résumé concis de 2 à 3 phrases pour l'article suivant :\n\nTITRE: {title}\nCONTENU: {content}"
    )
    summary_chain = summary_prompt | llm

    for article in articles_with_content:
        try:
            response = summary_chain.invoke({
                "title": article["title"],
                "content": article["content"][:4000]
            })
            article["summary"] = response.content
        except Exception as e:
            print(f"Erreur de résumé pour {article['title']}: {e}")
            article["summary"] = "Impossible de générer un résumé."

    # Construire le rapport final
    report_parts = [f"# Rapport de Veille pour : {state['query']}\n\nVoici un résumé des derniers articles de Techmeme :\n"]
    for article in articles_with_content:
        report_parts.append(f"## {article['title']}")
        
        # =========================================================================
        # === CORRECTION : On ajoute article['date'] dans la ligne Source       ===
        # =========================================================================
        # On récupère la date, avec une valeur par défaut si elle n'existe pas
        date_str = article.get('date', 'Date non spécifiée')
        report_parts.append(f"**Source:** [{article['url']}]({article['url']}) | **Date :** {date_str}")
        # =========================================================================
        
        report_parts.append(f"**Résumé:** {article['summary']}\n")
    
    state["final_report"] = "\n".join(report_parts)
    return state
# --- Construction du Graphe (Simple et Linéaire) ---
def create_langgraph_app():
    graph = StateGraph(AgentState)
    graph.add_node("scrape_homepage", scrape_techmeme_homepage)
    graph.add_node("extract_content", extract_full_content)
    graph.add_node("generate_report", summarize_and_report)
    graph.set_entry_point("scrape_homepage")
    graph.add_edge("scrape_homepage", "extract_content")
    graph.add_edge("extract_content", "generate_report")
    graph.add_edge("generate_report", END)
    return graph.compile()

langgraph_app = create_langgraph_app()

# --- Runner ---
async def run_veile_workflow(query: str) -> Dict:
    initial_state = {"query": query, "found_articles": [], "processed_articles": [], "final_report": None, "error_message": None}
    try:
        final_state = await langgraph_app.ainvoke(initial_state)
        return final_state
    except Exception as e:
        return {"error_message": f"Erreur critique du workflow: {e}"}