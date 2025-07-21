# api.py

from fastapi import FastAPI, HTTPException, Query
from typing import Dict, Any
from scraap import run_veile_workflow
# Crée une instance de l'application FastAPI
app = FastAPI(
    title="Agent de Veille Stratégique pour l'Afrique",
    description="Une API pour lancer un agent LangGraph qui scrape et analyse l'actualité tech.",
    version="1.0.0"
)


# Définition de l'endpoint racine (pour vérifier que l'API est en ligne)
@app.get("/")
def read_root():
    """
    Endpoint de base pour confirmer que l'API est fonctionnelle.
    """
    return {"status": "Agent de Veille API is running"}


# Définition de l'endpoint principal pour lancer la veille
@app.get("/veille", response_model=Dict[str, Any])
async def lancer_veille(
    query: str = Query(
        ...,  # Le "..." signifie que ce paramètre est obligatoire
        min_length=3,
        title="Sujet de la veille",
        description="Le thème ou la question pour guider la veille stratégique. Ex: 'Tendances Fintech en Afrique'"
    )
):
    """
    Lance le workflow complet de veille technologique.
    
    Ce processus peut prendre une à deux minutes en fonction du nombre de sites et de la charge du LLM.
    """
    print(f"Lancement de la veille pour la requête : '{query}'")
    try:
        # Comme notre workflow est asynchrone, on utilise `await` pour l'appeler.
        # FastAPI gère la boucle d'événements pour nous.
        result = await run_veile_workflow(query)
        
        if result.get("error_message"):
            # Si le workflow retourne une erreur gérée, on la renvoie comme une erreur HTTP
            raise HTTPException(status_code=500, detail=result["error_message"])
            
        print("Veille terminée avec succès.")
        return result

    except Exception as e:
        # Gère les erreurs inattendues qui pourraient survenir
        print(f"Erreur inattendue dans l'API : {e}")
        raise HTTPException(status_code=500, detail=f"Une erreur interne inattendue est survenue : {str(e)}")