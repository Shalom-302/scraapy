
import streamlit as st
import pandas as pd
import asyncio # Import nécessaire pour gérer l'asynchronisme

# On importe directement la fonction du backend
from scraap import run_veile_workflow

# --- Configuration de la Page ---
st.set_page_config(layout="wide", page_title="SCRAAPY - Veille Automatisée")

# --- Initialisation de l'état (inchangé) ---
if "final_state" not in st.session_state:
    st.session_state["final_state"] = None

# --- Barre Latérale (inchangée) ---
with st.sidebar:
    st.image("https://img.icons8.com/plasticine/100/bot.png", width=80)
    st.markdown("## SCRAAPY")
    st.markdown("### Votre Outil de Veille")
    
    custom_query = st.text_input(
        "Quel est le sujet de votre veille ?", 
        "Tendances en technologie actuellement"
    )
    
    st.markdown("---")
    
    # =========================================================================
    # === CORRECTION : Le bouton appelle maintenant le backend directement    ===
    # ===            en utilisant asyncio.run() pour gérer l'asynchronisme  ===
    # =========================================================================
    if st.button("🚀 Lancer la Veille", use_container_width=True):
        with st.spinner("Lancement du scraping et de l'analyse... Le traitement peut prendre une minute..."):
            try:
                # C'EST LA LIGNE MAGIQUE : on lance la fonction async depuis notre script sync
                final_state_result = asyncio.run(run_veile_workflow(custom_query))
                
                # Stocker le résultat et rafraîchir la page
                st.session_state["final_state"] = final_state_result
                st.rerun()

            except Exception as e:
                # Gérer les erreurs qui pourraient survenir pendant l'exécution
                st.error(f"Une erreur critique est survenue durant l'exécution : {e}")
                st.session_state["final_state"] = {"error_message": str(e)}

# --- Affichage Principal ---
st.title("🤖 SCRAAPY : Votre Assistant de Veille Intelligente")
final_state = st.session_state.get("final_state")

if not final_state:
    st.info("👋 Bienvenue ! Indiquez le sujet de votre veille et cliquez sur 'Lancer la Veille'.")
    st.stop()

# --- Affichage des Résultats (inchangé) ---
# Le reste de votre code d'affichage est parfait
if final_state.get("error_message"):
    st.error(f"❌ Une erreur est survenue lors du traitement : {final_state['error_message']}")

elif final_state.get("final_report"):
    st.success("✅ Veille terminée avec succès !")
    st.subheader("📊 Rapport de Synthèse")
    st.markdown(final_state["final_report"])
    
    # ... (le reste de votre code d'affichage des articles est bon) ...
else:
    st.warning("Le processus a terminé, mais aucun rapport n'a été généré.")