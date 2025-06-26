# backend_scraapy.py

import os
from typing import List, Dict, TypedDict, Optional
from dotenv import load_dotenv

from tavily import TavilyClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_deepseek import ChatDeepSeek
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
import trafilatura

# --- Configuration et Initialisation ---
load_dotenv()

# Clés API
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Assurez-vous que les clés sont bien chargées
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY n'est pas configurée dans les variables d'environnement.")
if not DEEPSEEK_API_KEY:
    raise ValueError("GOOGLE_API_KEY n'est pas configurée dans les variables d'environnement.")

# Initialisation des clients API
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # other params...
)
# --- Configuration LangSmith (IMPORTANT pour l'observabilité) ---
# Utilisation des variables d'environnement préfixées par LANGSMITH_ comme dans votre .env
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGSMITH_TRACING", "true") # Permet de charger true/false
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY") # C'est la ligne clé à modifier
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT") 

# Vérification supplémentaire pour s'assurer que la clé est bien chargée
if not os.getenv("LANGSMITH_API_KEY"):
    print("Attention: LANGSMITH_API_KEY n'est pas configurée. Le traçage LangSmith pourrait ne pas fonctionner.")

# --- Définition de l'État du Graphe ---
class DetailedArticle(TypedDict):
    title: str
    url: str
    content: str # Contenu complet de l'article après scraping
    summary: str # Résumé généré par LLM
    insights: Dict # Insights extraits par le LLM (ex: {"themes": ["AI"], "organisations": ["Google"]})

class AgentState(TypedDict):
    query: str # La requête initiale de l'utilisateur
    time_filter: str # Le filtre de temps choisi par l'utilisateur
    search_results: List[Dict] # Résultats bruts de Tavily
    processed_articles: List[DetailedArticle] # Articles enrichis (contenu complet, résumé, insights)
    final_report: Optional[str] # Le rapport final généré
    error_message: Optional[str] # Pour la gestion d'erreurs

# --- Nœuds (Agents) du Graphe LangGraph ---

ALLOWED_DOMAINS = [
    "techcrunch.com",
    "theverge.com",
    "numerama.com",
    "frandroid.com",
    "01net.com",
    "zdnet.fr",
    "clubic.com",
    "tomshardware.fr"
]

def call_tavily_search(state: AgentState) -> AgentState:
    print("---NODE: Calling Tavily Search---")
    query = state["query"]
    time_filter = state["time_filter"]

    days_map = {
        "Aujourd'hui": 1,
        "Hier": 2,
        "Cette semaine": 7
    }

    try:
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            time_published_days=days_map.get(time_filter, 1),
            max_results=5,
            include_domains=ALLOWED_DOMAINS
        )
        raw_results = response['results']

        # 🔒 Filtrage des domaines autorisés (par sécurité)
        filtered_results = [
            r for r in raw_results if any(domain in r['url'] for domain in ALLOWED_DOMAINS)
        ]

        if not filtered_results:
            state["error_message"] = "Aucun résultat pertinent trouvé parmi les sources gratuites."
        else:
            state["search_results"] = filtered_results

        return state

    except Exception as e:
        state["error_message"] = f"Erreur lors de la recherche Tavily : {e}"
        print(f"Error in call_tavily_search: {e}")
        return state


    except Exception as e:
        state["error_message"] = f"Erreur lors de la recherche Tavily : {e}"
        print(f"Error in call_tavily_search: {e}")
        return state


def extract_content(state: AgentState) -> AgentState:
    """Extrait le contenu complet des URLs."""
    print("---NODE: Extracting Content---")
    search_results = state["search_results"]
    processed_articles: List[DetailedArticle] = []

    for result in search_results:
        url = result['url']
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded, favor_recall=True, include_comments=False,
                                          include_tables=False, include_links=False, include_images=False)
                if text:
                    # Trafilatura fait déjà un bon nettoyage, pas besoin de clean_extra_whitespace/clean_non_ascii_chars
                    processed_articles.append({
                        "title": result.get('title', 'N/A'),
                        "url": url,
                        "content": text,
                        "summary": "",
                        "insights": {}
                    })
                else:
                    print(f"Contenu non extractible par Trafilatura pour : {url}")
            else:
                print(f"Impossible de télécharger l'URL : {url}")

        except Exception as e:
            print(f"Erreur lors de l'extraction de {url}: {e}")
            # Si une erreur se produit, on peut ajouter un article vide ou un message d'erreur spécifique
            processed_articles.append({
                "title": result.get('title', 'N/A'),
                "url": url,
                "content": f"Erreur d'extraction: {e}",
                "summary": "Contenu non disponible en raison d'une erreur d'extraction.",
                "insights": {}
            })

    state["processed_articles"] = processed_articles
    return state

# Définition du schéma d'insights attendu
class ArticleInsights(BaseModel):
    summary: str = Field(description="Un résumé concis et informatif de l'article en tech.")
    main_topics: List[str] = Field(description="Liste des sujets principaux abordés dans l'article.")
    key_entities: List[str] = Field(description="Liste des personnes, organisations, lieux clés mentionnés.")
    sentiment: str = Field(description="Le sentiment général de l'article (positif, négatif, neutre).")
    actionable_points: List[str] = Field(description="Points d'action ou implications potentielles extraits de l'article, si applicables.")

parser = JsonOutputParser(pydantic_object=ArticleInsights)

summary_insight_prompt = ChatPromptTemplate.from_messages([
    ("system", "Vous êtes un analyste de veille stratégique en tech. Créez un rapport concis et pertinent à partir des articles et insights fournis. Le rapport doit mettre en évidence les points clés, les tendances émergentes et les implications pour l'utilisateur, en réponse à la requête initiale. Organisez-le de manière claire avec des titres, des sous-titres et des listes. Répondez au format JSON spécifié.\n{format_instructions}"),
    ("human", "Article à analyser : \n\n{article_content}"),
]).partial(format_instructions=parser.get_format_instructions())

def summarize_and_extract_insights(state: AgentState) -> AgentState:
    """Résume et extrait les insights de chaque article."""
    print("---NODE: Summarizing and Extracting Insights---")
    processed_articles = state["processed_articles"]
    
    # Filtrer les articles qui n'ont pas de contenu valide (suite à une erreur d'extraction par exemple)
    articles_to_process = [a for a in processed_articles if a["content"] and "Erreur d'extraction" not in a["content"]]

    for article in articles_to_process:
        try:
            chain = summary_insight_prompt | llm | parser
            response = chain.invoke({"article_content": article["content"][:8000]}) # Limiter la taille du contenu pour le LLM
            
            article["summary"] = response.get("summary", "Résumé non disponible.")
            article["insights"] = {
                "main_topics": response.get("main_topics", []),
                "key_entities": response.get("key_entities", []),
                "sentiment": response.get("sentiment", "neutre"),
                "actionable_points": response.get("actionable_points", [])
            }
        except Exception as e:
            print(f"Erreur lors de l'analyse de l'article {article['url']}: {e}")
            article["summary"] = "Erreur lors de la génération du résumé/insights."
            article["insights"] = {"error": str(e)} # Ajouter l'erreur pour débogage
            
    state["processed_articles"] = processed_articles
    return state

report_prompt = ChatPromptTemplate.from_messages([
    ("system", "Vous êtes un analyste de veille stratégique. Créez un rapport concis et pertinent à partir des articles et insights fournis. Le rapport doit mettre en évidence les points clés, les tendances émergentes et les implications pour l'utilisateur, en réponse à la requête initiale. Organisez-le de manière claire avec des titres, des sous-titres et des listes, en utilisant le format Markdown."),
    ("human", "Requête initiale : {query}\n\nArticles et insights :\n\n{processed_articles_str}")
])

def generate_final_report(state: AgentState) -> AgentState:
    """Génère le rapport final de veille."""
    print("---NODE: Generating Final Report---")
    query = state["query"]
    processed_articles = state["processed_articles"]
    
    processed_articles_str = ""
    for i, article in enumerate(processed_articles):
        # N'inclure que les articles qui ont été traités avec succès
        if "Erreur d'extraction" not in article["content"] and "Erreur lors de la génération" not in article["summary"]:
            processed_articles_str += f"### Article #{i+1}: {article['title']}\n"
            processed_articles_str += f"URL: [{article['url']}]({article['url']})\n"
            processed_articles_str += f"**Résumé:** {article['summary']}\n"
            if article['insights']:
                processed_articles_str += "**Insights:**\n"
                for k, v in article['insights'].items():
                    if isinstance(v, list) and v:
                        processed_articles_str += f"- **{k.replace('_', ' ').title()}:** {', '.join(v)}\n"
                    elif isinstance(v, str) and v:
                         processed_articles_str += f"- **{k.replace('_', ' ').title()}:** {v}\n"
            processed_articles_str += "\n---\n\n"
        else:
            processed_articles_str += f"### Article #{i+1}: {article['title']} (Problème lors du traitement)\n"
            processed_articles_str += f"URL: [{article['url']}]({article['url']})\n"
            processed_articles_str += f"Détails: {article.get('summary', 'Non disponible')}\n\n---\n\n"
        
    if not processed_articles_str.strip(): # Si aucun article n'a pu être traité
        state["final_report"] = "Aucun article pertinent n'a pu être traité pour générer un rapport."
        return state

    try:
        chain = report_prompt | llm
        report = chain.invoke({
            "query": query,
            "processed_articles_str": processed_articles_str
        })
        state["final_report"] = report.content
        return state
    except Exception as e:
        state["error_message"] = f"Erreur lors de la génération du rapport : {e}"
        print(f"Error in generate_final_report: {e}")
        return state

# --- Construction et Compilation du Graphe LangGraph ---

def create_langgraph_app():
    """Crée et compile le workflow LangGraph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("search", call_tavily_search)
    workflow.add_node("extract_content", extract_content)
    workflow.add_node("summarize_and_extract_insights", summarize_and_extract_insights)
    workflow.add_node("generate_final_report", generate_final_report)

    workflow.set_entry_point("search")
    workflow.add_edge("search", "extract_content")
    workflow.add_edge("extract_content", "summarize_and_extract_insights")
    workflow.add_edge("summarize_and_extract_insights", "generate_final_report")
    workflow.add_edge("generate_final_report", END)

    return workflow.compile()

# L'application LangGraph compilée, prête à être importée
langgraph_app = create_langgraph_app()

# Fonction d'entrée pour le frontend
def run_veile_workflow(query: str, time_filter: str) -> Dict:
    """
    Exécute le workflow de veille LangGraph et retourne l'état final.
    Cette fonction sera appelée par le frontend.
    """
    initial_state: AgentState = {
        "query": query,
        "time_filter": time_filter,
        "search_results": [],
        "processed_articles": [],
        "final_report": None,
        "error_message": None
    }
    
    try:
        # Utilisez l'application compilée
        final_state = langgraph_app.invoke(initial_state)
        return final_state
    except Exception as e:
        # Gérer les erreurs au niveau supérieur pour le frontend
        return {
            "query": query,
            "time_filter": time_filter,
            "search_results": [],
            "processed_articles": [],
            "final_report": None,
            "error_message": f"Une erreur inattendue est survenue lors de l'exécution du workflow: {e}"
        }