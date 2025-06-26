# scheduler_streamlit.py

import time
import threading
import json
from datetime import datetime
from scraap import run_veile_workflow

DEFAULT_QUERY = "Principales actualités dans le monde de la tech"
DEFAULT_TIME_FILTER = "Aujourd'hui"
SAVE_PATH = "last_auto_report.json"

def job_scheduler():
    while True:
        print("⏰ [SCHEDULER] Lancement du workflow automatique...")
        try:
            result = run_veile_workflow(DEFAULT_QUERY, DEFAULT_TIME_FILTER)
            result["executed_at"] = datetime.utcnow().isoformat()

            # Sauvegarde dans un fichier JSON local
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=4)

            print("✅ [SCHEDULER] Rapport automatique sauvegardé avec succès.")
        except Exception as e:
            print(f"❌ [SCHEDULER] Erreur : {e}")

        time.sleep(60 * 60)  # Toutes les heures
