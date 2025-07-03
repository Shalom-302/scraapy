# api.py (ou main.py) - Version finale et cohérente

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict

# Importer la fonction principale de notre logique backend
from scraap import run_veile_workflow

# =========================================================================
# === CORRECTION : Le modèle de requête n'attend plus que la 'query'    ===
# =========================================================================
class VeilleRequest(BaseModel):
    query: str

# Création de l'application FastAPI
app = FastAPI(
    title="SCRAAPY Veille API",
    description="API pour lancer un agent de veille technologique."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "SCRAAPY API est en ligne"}

@app.post("/run-veille", response_model=Dict)
async def run_veille_endpoint(request: VeilleRequest):
    """
    Lance le workflow de veille avec la requête fournie.
    """
    print(f"Requête de veille reçue. Contexte du rapport : '{request.query}'")
    
    # =========================================================================
    # === CORRECTION : L'appel de la fonction n'a plus qu'un seul argument  ===
    # =========================================================================
    final_state = await run_veile_workflow(request.query)
    
    return final_state