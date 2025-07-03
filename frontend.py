# frontend.py (Version finale, connectée à l'API FastAPI)

import streamlit as st
import pandas as pd
from collections import Counter
import requests # Seul import nécessaire pour la communication

# --- Configuration de la Page ---
st.set_page_config(layout="wide", page_title="SCRAAPY - Veille Automatisée")

# L'URL de notre serveur FastAPI. Assurez-vous qu'il est en cours d'exécution.
FASTAPI_URL = "http://127.0.0.1:8000/run-veille"

# --- Initialisation de l'état de la session (inchangé) ---
if "final_state" not in st.session_state:
    st.session_state["final_state"] = None

# --- Barre Latérale : Le Centre de Contrôle ---
with st.sidebar:
    st.image("https://img.icons8.com/plasticine/100/bot.png", width=80)
    st.markdown("## SCRAAPY")
    st.markdown("### Votre Outil de Veille")
    
    # Le champ 'query' est le seul qui est envoyé à l'API
    custom_query = st.text_input(
        "Quel est le sujet de votre veille ?", 
        "Tendances en technologie actuellement"
    )
    
    # On garde le filtre de date pour l'esthétique, mais il n'est plus utilisé par le backend
    # st.radio("Période (pour information) :", ["Aujourd'hui", "Cette semaine"])
    
    st.markdown("---")
    
    # =========================================================================
    # === CORRECTION : Le bouton appelle maintenant l'API FastAPI           ===
    # =========================================================================
    if st.button("🚀 Lancer la Veille", use_container_width=True):
        with st.spinner("Connexion au serveur de veille... Le traitement peut prendre une minute..."):
            # Préparation des données à envoyer à l'API (juste la query)
            payload = {"query": custom_query}
            
            try:
                # Envoi de la requête POST à l'API avec un timeout
                response = requests.post(FASTAPI_URL, json=payload, timeout=600) # 5 minutes
                
                # Vérifier si la requête a réussi (status code 200)
                response.raise_for_status() 
                
                # Stocker la réponse JSON dans l'état de la session
                st.session_state["final_state"] = response.json()
                
                # Rafraîchir la page pour afficher les nouveaux résultats
                st.rerun()

            except requests.exceptions.Timeout:
                st.error("Erreur : Le serveur a mis trop de temps à répondre (Timeout).")
            except requests.exceptions.RequestException as e:
                st.error(f"Erreur de connexion au serveur de veille : {e}")
                st.session_state["final_state"] = {"error_message": str(e)}

# --- Affichage Principal ---
st.title("🤖 SCRAAPY : Votre Assistant de Veille Intelligente")
final_state = st.session_state.get("final_state")

if not final_state:
    st.info("👋 Bienvenue ! Indiquez le sujet de votre veille dans la barre latérale et cliquez sur 'Lancer la Veille' pour commencer.")
    st.stop()

# --- Affichage des Résultats de la Veille ---
# Le reste de votre code d'affichage est parfait et n'a pas besoin de changer.
# Il lira simplement les données que l'API a retournées.

if final_state.get("error_message"):
    st.error(f"❌ Une erreur est survenue lors du traitement : {final_state['error_message']}")

elif final_state.get("final_report"):
    st.success("✅ Veille terminée avec succès !")
    
    st.subheader("📊 Rapport de Synthèse")
    st.markdown(final_state["final_report"])
    
    st.markdown("---")
    
    processed_articles = final_state.get("found_articles", []) # Utilise found_articles pour le compte
    st.subheader(f"📚 {len(processed_articles)} Articles Sources Analysés")
    
    if processed_articles:
        with st.expander("Cliquez pour voir les détails des articles"):
            for i, article in enumerate(final_state.get("processed_articles", [])):
                st.markdown(f"#### {i+1}. {article['title']}")
                st.markdown(f"**Source:** [{article['url']}]({article['url']})")
                
                if article.get("summary"):
                    st.markdown(f"**Résumé :** {article['summary']}")
                else:
                    st.caption("Résumé non disponible pour cet article.")
                
                st.markdown("---")
else:
    st.warning("Le processus a terminé, mais aucun rapport n'a été généré. Il est possible qu'aucun article n'ait pu être traité.")
    
  