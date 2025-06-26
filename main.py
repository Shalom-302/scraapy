import streamlit as st
import pandas as pd
from typing import Dict, List
from datetime import datetime, timezone, timedelta



import logging
logging.basicConfig(level=logging.DEBUG)

from scraap import run_veile_workflow, DetailedArticle, AgentState

st.set_page_config(layout="wide", page_title="SCRAAPY - Veille Automatisée")

# --- Barre Latérale ---
with st.sidebar:
    st.markdown("## SCRAAPY")
    st.markdown("### Paramètres de Veille")
    selected_date_filter = st.radio("Période :", ["Aujourd'hui", "Hier", "Cette semaine"], index=0)
    custom_query = st.text_input("Requête :", "Principales actualités dans le monde de la tech")
    st.markdown("---")
    st.info("⏱️ La veille se lance automatiquement si plus d'1h s'est écoulée.")

# --- Vérification du moment de la dernière exécution ---
def should_rerun():
    last_run_str = st.session_state.get("executed_at")
    if last_run_str:
        last_run = datetime.fromisoformat(last_run_str)
        now = datetime.now(timezone.utc)
        return (now - last_run) > timedelta(hours=1)
    return True  #

# --- Exécution automatique du workflow si besoin ---
if "data_loaded" not in st.session_state:
    st.session_state["data_loaded"] = False

if should_rerun() or not st.session_state["data_loaded"]:
    st.session_state["data_loaded"] = True
    with st.spinner("🚀 Lancement de la veille automatisée..."):
        final_state: AgentState = run_veile_workflow(custom_query, selected_date_filter)
        st.session_state["final_state"] = final_state
        st.session_state["last_processed_articles"] = final_state.get("processed_articles", [])
        st.session_state["executed_at"] = datetime.utcnow().isoformat()

# --- Affichage des résultats ---
final_state = st.session_state.get("final_state", {})

st.title("SCRAAPY : Votre Assistant de Veille Intelligente")
st.caption(f"🕒 Veille générée le : {st.session_state.get('executed_at', '').replace('T', ' ')[:19]} UTC")
st.subheader(f"Rapport : '{custom_query}' ({selected_date_filter})")

if final_state.get("error_message"):
    st.error(f"❌ Erreur : {final_state['error_message']}")
elif final_state.get("final_report"):
    st.success("✅ Veille réussie !")
    st.markdown("---")
    st.subheader("📊 Rapport de Veille")
    st.markdown(final_state["final_report"])

    if final_state.get("processed_articles"):
        st.markdown("---")
        st.subheader("📚 Articles Sources")
        with st.expander(f"Voir les {len(final_state['processed_articles'])} articles analysés"):
            for i, article in enumerate(final_state["processed_articles"]):
                st.markdown(f"#### {i+1}. {article['title']}")
                st.markdown(f"**Source :** [{article['url']}]({article['url']})")
                st.markdown(f"**Résumé :** {article.get('summary', 'Non disponible')}")
                insights = article.get("insights", {})
                if insights:
                    st.markdown("**Insights Clés :**")
                    for k, v in insights.items():
                        if isinstance(v, list) and v:
                            st.markdown(f"- **{k.replace('_', ' ').title()}:** {', '.join(v)}")
                        elif isinstance(v, str) and v:
                            st.markdown(f"- **{k.replace('_', ' ').title()}:** {v}")
                st.markdown("---")
    else:
        st.warning("Aucun article traité ou contenu inaccessible.")
else:
    st.warning("Le workflow a terminé mais aucun rapport n'a été généré.")

# --- Statistiques ---
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### Statistiques")
    st.metric("Articles analysés", len(st.session_state.get("last_processed_articles", [])))
with col2:
    st.markdown("### Tendance (Exemple)")
    chart_data = pd.DataFrame({'value': [100, 200, 150, 300], 'index': range(4)})
    st.line_chart(chart_data, use_container_width=True)
