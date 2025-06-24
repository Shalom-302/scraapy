
---

````markdown
# 📰 Scraapy — Dashboard de Veille d'Actualités avec Streamlit & IA Avancée

**Scraapy** est une application robuste et intelligente, conçue pour transformer la simple consultation d'actualités en une **veille stratégique automatisée**. Grâce à un workflow avancé propulsé par **LangGraph**, elle extrait, analyse et synthétise des informations cruciales en temps réel, offrant des rapports de veille personnalisés.

---

## 🎯 Fonctionnalités Clés

- 🔎 **Recherche Avancée** : Utilise [Tavily API](https://tavily.com) pour une recherche d'actualités pertinente.
- 🧠 **Intelligence Artificielle Avancée** : Intègre les **LLMs (Large Language Models)** comme **DeepSeek** ou **Gemini** pour une analyse textuelle fine.
- 🔗 **Workflows IA Complexes** : Grâce à **LangGraph**, orchestre automatiquement la recherche, le scraping, le résumé et l'extraction d'insights.
- 📊 **Rapports de Veille Structurés** : Génère des synthèses claires contenant résumés, entités clés, sujets dominants et points d'action.
- 🛠️ **Observabilité avec LangSmith** : Suivi complet des étapes du workflow IA pour le débogage et la transparence.
- ⚡ **Mise en Cache Intelligente** : Optimisation des appels API via `@st.cache_data`.
- 🌐 **Interface Intuitive** : Construite avec [Streamlit](https://streamlit.io), facile à utiliser.
- 🗂️ **Filtres Dynamiques de Temps** : Filtrage rapide par "Aujourd’hui", "Hier" ou "Cette semaine".

---

## 🧱 Stack Technologique

- `streamlit` — Interface utilisateur interactive
- `langchain-google-genai` ou `langchain-community` — Pour l'accès aux LLMs (Gemini, DeepSeek, etc.)
- `langgraph` — Création de workflows d'agents IA
- `tavily-python` — Recherche d’actualités via Tavily
- `trafilatura` — Extraction propre de contenu HTML
- `pydantic` — Définition de schémas de données fiables
- `python-dotenv` — Gestion des clés API via `.env`
- `pandas` — Traitement léger des données pour les graphiques
- `langsmith` — Outil de suivi et d’analyse des chaînes LLM

---

## 🛠️ Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/Shalom-302/scraapy.git
cd scraapy
````

### 2. Créer et activer un environnement virtuel

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# Ou .venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

#### Exemple de contenu pour `requirements.txt` :

```txt
streamlit
pandas
python-dotenv
tavily-python
langchain-google-genai
langchain-community
langchain-core
langgraph
trafilatura
unstructured
pydantic
```

---

### 4. Configurer les clés API

Créez un fichier `.env` à la racine du projet :

```env
# Tavily pour la recherche d’actualités
TAVILY_API_KEY="votre_clé_tavily"

# LLM de votre choix
DEEPSEEK_API_KEY="votre_clé_deepseek"
# ou, pour Gemini
GOOGLE_API_KEY="votre_clé_gemini"

# LangSmith pour le traçage
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="votre_clé_langsmith"
LANGCHAIN_PROJECT="Nom_du_projet"
```

#### 🔑 Où obtenir vos clés :

* **Tavily** : [https://tavily.com](https://tavily.com)
* **DeepSeek** : [https://platform.deepseek.com/api\_keys](https://platform.deepseek.com/api_keys)
* **Gemini** : [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
* **LangSmith** : [https://smith.langchain.com/settings](https://smith.langchain.com/settings)

---

## ▶️ Lancer l'application

L'application est divisée en deux fichiers :

* `scraap.py` → backend IA LangGraph
* `main.py` → interface utilisateur Streamlit

### Lancer l'interface :

```bash
streamlit run main.py
```

> Streamlit ouvrira automatiquement l’interface dans [http://localhost:8501](http://localhost:8501)

---

## 🧪 Conseils de Développement

* 🧭 **LangSmith est votre boussole** : visualisez tous les états et noeuds du workflow IA.
* 📺 **Gardez un œil sur votre terminal** : les `print()` et erreurs y apparaissent directement.
* 📦 **Utilisez le cache intelligemment** : `@st.cache_data` réduit les appels API coûteux.

---

## 📌 Roadmap (Prochaines étapes)

* [ ] Exporter les rapports en PDF
* [ ] Authentification utilisateur avec Firebase/Auth0
* [ ] Multi-agent LangGraph avec classification de domaine
* [ ] Intégration avec Notion / Slack pour les alertes

---
