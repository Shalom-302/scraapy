# frontend_scraapy.py

import streamlit as st
import pandas as pd
from typing import Dict, List
import logging
logging.basicConfig(level=logging.DEBUG)


# Importez la fonction du backend
from scraap import run_veile_workflow, DetailedArticle, AgentState # Importez AgentState et DetailedArticle pour les types


# --- Configuration de la Page Streamlit ---
st.set_page_config(layout="wide", page_title="SCRAAPY - Veille Automatisée")

# --- Barre Latérale (Sidebar) ---
with st.sidebar:
    st.markdown("## SCRAAPY")
    st.text_input("Naviguer...", placeholder="Naviguer...")
    st.markdown("<p style='font-size:10px; text-align:right;'>⌘K</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.radio("Navigation", ["Scraapy", "Pour vous"], index=0, key="main_nav")
    st.markdown("---")
    st.markdown("### Filtres de Temps")
    selected_date_filter = st.radio("Période :", ["Aujourd'hui", "Hier", "Cette semaine"], index=0, key="date_filter")
    
    st.markdown("---")
    st.markdown("### Personnaliser la Veille")
    custom_query = st.text_input(
        "Requête de veille :", 
        value="Principales actualités dans le monde actuel", # Exemple de requête plus spécifique
        key="custom_query"
    )
    
    st.markdown("---")
    st.markdown("### Explorer")
    st.radio("Catégories :", ["Tendances", "En direct"], key="explore_filter")


# --- Contenu Principal ---
st.title("SCRAAPY : Votre Assistant de Veille Intelligente")
st.subheader(f"Génération de rapports basés sur : '{custom_query}' pour la période '{selected_date_filter}'")

# Bouton pour lancer le workflow LangGraph
if st.button("Lancer la Veille Automatisée"):
    st.markdown("---")
    # Utilisation de st.spinner pour montrer que le traitement est en cours
    with st.spinner("🚀 Lancement du workflow de veille LangGraph... C'est parti pour l'analyse !"):
        # Appel de la fonction du backend
        final_state: AgentState = run_veile_workflow(custom_query, selected_date_filter)

        if final_state.get("error_message"):
            st.error(f"Une erreur est survenue lors de la veille : {final_state['error_message']}")
            st.info("Vérifiez les logs de votre terminal et les traces LangSmith pour plus de détails.")
        elif final_state.get("final_report"):
            st.success("✅ Veille terminée avec succès ! Voici votre rapport.")
            st.markdown("---")
            st.subheader("📊 Rapport de Veille Détaillé")
            st.markdown(final_state["final_report"]) # Afficher le rapport formaté en Markdown
            
            # Stocker les articles traités pour affichage persistant
            st.session_state['last_processed_articles'] = final_state.get("processed_articles", [])

            # Optionnel : Afficher les détails des articles traités dans une section déroulante
            if final_state.get("processed_articles"):
                st.markdown("---")
                st.subheader("📚 Articles Sources Analysés")
                with st.expander(f"Voir les {len(final_state['processed_articles'])} articles sources détaillés"):
                    for i, article in enumerate(final_state["processed_articles"]):
                        st.markdown(f"#### {i+1}. {article['title']}")
                        st.markdown(f"**Source :** [{article['url']}]({article['url']})")
                        if "Erreur d'extraction" in article["content"] or "Erreur lors de la génération" in article["summary"]:
                             st.warning(f"Problème lors du traitement de cet article : {article.get('summary', 'N/A')}")
                        else:
                            st.markdown(f"**Résumé :** {article['summary']}")
                            if article['insights']:
                                st.markdown("**Insights Clés :**")
                                for k, v in article['insights'].items():
                                    if isinstance(v, list) and v:
                                        st.markdown(f"- **{k.replace('_', ' ').title()}:** {', '.join(v)}")
                                    elif isinstance(v, str) and v:
                                        st.markdown(f"- **{k.replace('_', ' ').title()}:** {v}")
                        st.markdown("---")
            else:
                st.info("Aucun article n'a pu être traité pour générer des insights.")
        else:
            st.warning("Le workflow a terminé mais aucun rapport n'a été généré. Il pourrait y avoir un problème.")
            st.info("Vérifiez les logs de votre terminal et les traces LangSmith pour plus de détails.")

# --- Section "Articles analysés" et graphique ---
# Afficher le nombre d'articles traités à partir de la dernière exécution réussie
col_articles_count, col_summary_chart = st.columns([3, 1])

with col_articles_count:
    st.markdown("---")
    st.markdown("### Statistiques de la dernière veille")
    num_processed = len(st.session_state.get('last_processed_articles', []))
    st.metric(label="Articles analysés", value=num_processed)
    
with col_summary_chart:
    st.markdown("---")
    st.markdown("### Tendance (Exemple)")
    # Ceci est un placeholder, vous pourriez le rendre dynamique avec de vraies métriques de veille
    chart_data = pd.DataFrame({'value': [100, 200, 150, 300, 250, 400], 'index': range(6)})
    st.line_chart(chart_data, use_container_width=True)