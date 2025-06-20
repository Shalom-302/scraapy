import streamlit as st
import pandas as pd
from tavily import TavilyClient
from dotenv import load_dotenv
import os
load_dotenv()
tavily_key= os.getenv("TAVILY_API_KEY")

tavily_client = TavilyClient(api_key=tavily_key)


# --- 2. Fonction de recherche avec mise en cache ---
# @st.cache_data est CRUCIAL pour la performance et pour ne pas gaspiller les appels API.
# Le cache est vidé toutes les heures (3600 secondes).
@st.cache_data(ttl=3600)
def search_news(time_filter: str):
    """
    Recherche les actualités avec Tavily en fonction d'un filtre de temps.
    """
    # Mapping des filtres de l'interface aux jours pour l'API Tavily
    # Note: "Hier" est interprété comme "dans les dernières 48h" pour inclure la journée d'hier.
    days_map = {
        "Aujourd'hui": 1,
        "Hier": 2,
        "Cette semaine": 7
    }
    
    # Définition de la requête de recherche
    query = "Principales actualités et nouvelles dans le monde actuellement"
    
    # Appel à l'API Tavily avec les paramètres avancés
    response = tavily_client.search(
        query=query,
        search_depth="advanced", # Nécessaire pour utiliser les filtres
        time_published_days=days_map.get(time_filter, 1), # Filtre par date
        max_results=5 # Limite à 5 résultats pour un affichage clair
    )
    
    # Retourne la liste des résultats
    return response['results']

# --- Barre Latérale (Sidebar) ---
# Votre code de sidebar est conservé tel quel.
with st.sidebar:
    st.markdown("## SCRAAPY")
    st.text_input("Naviguer...", placeholder="Naviguer...")
    st.markdown("<p style='font-size:10px; text-align:right;'>⌘K</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.radio("Navigation", ["Scraapy", "Pour vous"], index=0, key="main_nav")
    st.markdown("---")
    st.markdown("### À la Une")
    # La valeur de ce radio bouton va piloter notre recherche
    selected_date_filter = st.radio("Filtre", ["Aujourd'hui", "Hier", "Cette semaine"], index=0, key="date_filter")
    st.markdown("---")
    st.markdown("### Explorer")
    st.radio("Explore", ["Tendances", "En direct"], key="explore_filter")


# --- Contenu Principal ---
# Le titre est maintenant dynamique en fonction du filtre sélectionné
st.title(f"À la Une : {selected_date_filter}")
st.subheader(f"Actualités principales.")

col_articles, col_summary = st.columns([3, 1])

with col_articles:
    # --- 3. Appel à la fonction de recherche et affichage des résultats ---
    # Le spinner s'affiche pendant que la fonction search_news s'exécute (la première fois)
    with st.spinner(f"Recherche des actualités pour '{selected_date_filter}'..."):
        # On appelle notre fonction avec le filtre de la sidebar
        articles_from_tavily = search_news(selected_date_filter)

    if not articles_from_tavily:
        st.warning("Aucun article trouvé pour cette période.")
    else:
        # On parcourt les vrais résultats de Tavily
        for i, article in enumerate(articles_from_tavily):
            st.markdown(f"#### #{i + 1}")
            article_col1, article_col2 = st.columns([1, 4])
            
            with article_col1:
                # Tavily ne fournit pas d'image, on garde un placeholder
                st.image("https://i.imgur.com/3o1I0dF.png", width=100, caption="Image non fournie")
            
            with article_col2:
                # On affiche le titre et un extrait du contenu
                st.markdown(f"**{article['title']}**")
                st.caption(f"Source : {article['url']}")
                st.write(article['content']) # Affiche l'extrait fourni par Tavily
            st.markdown("---")

with col_summary:
    # Le reste de votre code est conservé
    st.markdown("##### Articles analysés")
    st.markdown(f"## {len(articles_from_tavily)}") # Le nombre est maintenant dynamique
    chart_data = pd.DataFrame({'value': [100, 200, 150, 300, 250, 400], 'index': range(6)})
    st.line_chart(chart_data, use_container_width=True)