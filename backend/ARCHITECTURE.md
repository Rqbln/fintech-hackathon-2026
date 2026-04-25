# RegAgent — Documentation Technique Détaillée

## Vue d'ensemble

RegAgent est une API Python (FastAPI) qui automatise la conformité DORA (Digital Operational Resilience Act) pour les banques. Elle ingère des contrats vendeurs PDF, en extrait les clauses pertinentes, les indexe dans un corpus RAG Vertex AI, puis permet à des agents Gemini d'évaluer les gaps de conformité.

---

## Ce qui a été créé sur GCP

### 1. Corpus RAG Vertex AI
- **Nom display** : `regagent-corpus-v1`
- **Ressource GCP** : `projects/regagent-dora-2026/locations/europe-west1/ragCorpora/<id>`
- **Région** : `europe-west1` (Belgique)
  - Pourquoi pas `europe-west9` (Paris, la région principale du projet) : **RAG Engine n'est pas disponible en `europe-west9`**. On utilise `europe-west1` qui reste dans l'UE, ce qui est acceptable pour la conformité DORA sur la souveraineté des données.
- **Contenu indexé** :
  - 24 contrats vendeurs (depuis le bucket `regagent-documents-eu`)
  - DORA Art. 30 — 8 articles (depuis `reference_data/dora_article_30.json`)
  - ISO 27001 — 7 contrôles (depuis `reference_data/iso27001_controls.json`)
  - Règles banque — 8 règles internes (depuis `reference_data/bank_rules_sample.json`)
  - Total : ~2 250 chunks dans le corpus

### 2. Document AI Processor (pré-existant)
- **ID** : `9a4312989d6fb591`
- **Type** : OCR généraliste (non-imageless)
- **Région** : `eu` (multi-région Europe)
- **Limite découverte en prod** : 15 pages max par requête en mode non-imageless (la doc officielle dit 30, mais le processor de ce projet est limité à 15 — découvert par erreur `PAGE_LIMIT_EXCEEDED` lors des tests)

### 3. Cloud Storage Buckets (pré-existants)
- **`regagent-documents-eu`** : contrats PDF uploadés par l'API + les 24 contrats vendors
- **`regagent-reference-eu`** : données de référence DORA/ISO (non utilisé directement dans la pipeline actuelle)

---

## Architecture de la pipeline d'ingestion

```
[Client HTTP]
     │
     │ POST /api/documents/upload (PDF + vendor_name)
     ▼
[FastAPI Router] app/routers/documents.py
     │
     ▼
[ExtractorAgent] app/agents/extractor.py
     ├──▶ [GCS Upload] app/services/storage.py
     │         └── gs://regagent-documents-eu/uploads/{doc_id}_{filename}
     │
     ├──▶ [Document AI OCR] app/services/document_ai.py
     │         ├── Split PDF si > 15 pages (pypdf)
     │         ├── ProcessRequest → Document AI API (eu)
     │         └── Retourne: pages_text + tables structurées
     │
     ├──▶ [Chunker LangChain] app/utils/chunker.py
     │         ├── RecursiveCharacterTextSplitter (séparateurs légaux FR/EN)
     │         └── Classification DORA par mot-clé → catégorie
     │
     └──▶ [RAG Upload] app/services/rag_engine.py
               ├── get_or_create_corpus() → corpus "regagent-corpus-v1"
               └── upload_file() → TransformationConfig(chunk_size=800, overlap=100)

[Réponse JSON] → document_id, total_clauses, total_sla_entries
```

---

## Détail de chaque fichier codé

### `app/services/document_ai.py`

**Pourquoi Document AI et pas juste pypdf ?**
pypdf extrait du texte brut mais perd la structure des tableaux SLA (lignes RTO/RPO, valeurs cibles). Document AI, c'est un OCR professionnel de Google qui :
- Reconnaît les tableaux et renvoie leurs cellules de façon structurée
- Fonctionne sur des PDF scannés (images) pas seulement des PDF natifs
- Produit des coordonnées de position (`text_anchor`) utilisables pour reconstruire chaque page

**Problème rencontré et fix** : Le processor `9a4312989d6fb591` a une limite de 15 pages par requête (pas 30 comme documenté). Pour les contrats de 38+ pages, on obtient `PAGE_LIMIT_EXCEEDED`. Fix : `_split_pdf()` découpe le PDF en tranches de 15 pages avec pypdf, chaque tranche est envoyée séparément à Document AI, puis les résultats sont fusionnés avec le bon offset de numéro de page.

```python
_PAGE_LIMIT = 15  # limite réelle découverte en production

def _split_pdf(content: bytes) -> list[tuple[bytes, int]]:
    # Retourne [(chunk_bytes, page_offset), ...]
    # page_offset = index de la première page du chunk dans le PDF original
```

**Optimisation** : `_client()` est décoré `@functools.lru_cache` → le client HTTP Document AI est instancié une seule fois pour toute la durée de vie du process.

---

### `app/services/rag_engine.py`

**Pourquoi Vertex AI RAG Engine et pas Vector Search ?**
Vector Search (l'autre option Vertex AI pour les embeddings) nécessite de créer un index qui prend **25-30 minutes** à construire. Inacceptable pour un hackathon. RAG Engine est entièrement managé :
- `rag.create_corpus()` : instantané
- `rag.upload_file()` : upload + chunking + embedding automatiques (quelques secondes)
- `rag.retrieval_query()` : recherche sémantique sans gestion d'endpoint

**Pattern `_initialized`** : `vertexai.init()` ne peut être appelé qu'une seule fois par process (sinon warnings/erreurs). Le module `vertex_ai.py` initialise Vertex AI sur `europe-west9` (pour Gemini), et `rag_engine.py` l'initialise sur `europe-west1` (pour RAG). Chacun a son propre guard `_initialized` pour éviter le double appel.

**API réelle vs documentation** : La documentation Vertex AI montrait `rag.upload_file(chunk_size=800)` en kwargs directs. En pratique, l'API exige un objet `TransformationConfig` :
```python
rag.upload_file(
    corpus_name=corpus_name,
    path=tmp_path,
    display_name=display_name,
    transformation_config=rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(chunk_size=800, chunk_overlap=100)
    ),
)
```
De même pour la requête, `similarity_top_k` n'existe pas — c'est `rag_retrieval_config=rag.RagRetrievalConfig(top_k=N)`.

**Flux upload** :
1. Écrit le texte dans un fichier `.txt` temporaire (`tempfile.NamedTemporaryFile`)
2. Appelle `rag.upload_file()` avec le path du fichier
3. RAG Engine gère lui-même le chunking et l'embedding (modèle `text-multilingual-embedding-002`)
4. Supprime le fichier temp dans le `finally` block

---

### `app/utils/chunker.py`

**Pourquoi un chunker custom si RAG Engine gère déjà le chunking ?**
RAG Engine découpe par taille de tokens sans connaître la structure du document. Les contrats ont une structure logique (articles, clauses, annexes). On veut que chaque chunk corresponde à une clause complète, pas à une tranche arbitraire au milieu d'une phrase. `RecursiveCharacterTextSplitter` de LangChain essaie d'abord de couper sur les séparateurs "importants" (changement d'article) avant de tomber sur les séparateurs de fallback (double newline, puis newline, puis espace).

**Séparateurs légaux** (dans l'ordre de priorité) :
```python
_LEGAL_SEPARATORS = [
    r"\n(?:Article|Section|Clause|Annexe|Annex|ARTICLE|SECTION)\s+\d+",  # début d'article
    r"\n\d+\.\d+\s",   # 1.1 , 2.3.1
    r"\n\d+\.\s",      # 1. , 2.
    "\n\n",            # paragraphe
    "\n",              # ligne
    " ",               # mot (dernier recours)
]
```

**Classification DORA** : chaque chunk est classé dans une catégorie DORA par recherche de mots-clés FR/EN avec regex. La classification est basée sur les 6 thèmes de l'Art. 30 de DORA (exigences pour les contrats avec prestataires TIC critiques) :

| Catégorie | Mots-clés FR/EN |
|---|---|
| `rto_rpo` | rto, rpo, recovery time, continuité, continuity |
| `audit_rights` | audit, inspection, droit de visite, contrôle |
| `data_residency` | résidence, residency, stockage, localisation, sovereign |
| `subcontracting` | sous-traitant, subcontract, fourth party |
| `incident_reporting` | incident, notification, signalement, breach |
| `exit_strategy` | exit, résiliation, portabilité, termination |
| `general` | tout le reste |

---

### `app/agents/extractor.py`

**Rôle** : Orchestrateur central. Il coordonne les 4 étapes de la pipeline et renvoie un `VendorDocument` Pydantic.

**`_format_for_rag()`** : Assemble les chunks en un seul texte avant upload. Format choisi :
```
[AWS | rto_rpo]
Le prestataire garantit un RTO de 4 heures pour les systèmes critiques.

[AWS | audit_rights]
Le client dispose d'un droit d'audit annuel...
```
Le préfixe `[vendor | category]` permet au RAG de retrouver les chunks par vendeur et par catégorie DORA dans les queries Gemini.

**`_extract_sla()`** : Tente d'extraire les métriques SLA depuis les tableaux Document AI. Cherche une colonne "metric/sla/rto/rpo" et une colonne "value/target/valeur". Ne produit des `SLAEntry` que si les deux colonnes sont trouvées.

**`document_id`** : UUID hex 8 chars généré à chaque upload. Sert de préfixe dans GCS pour éviter les collisions de noms de fichiers (`{doc_id}_{filename}`).

---

### `app/services/storage.py`

**Fix apporté** : `storage.Client()` sans projet lève `OSError: Project was not passed and could not be determined from the environment`. Fix : `storage.Client(project=GCP_PROJECT)` avec le project ID explicite depuis `config.py`.

---

### `app/services/vertex_ai.py`

**Deux clients séparés** : Ce module gère les appels Gemini (génération de texte) et les embeddings. Il est distinct de `rag_engine.py` car il utilise une région différente (`europe-west9` pour Gemini vs `europe-west1` pour RAG). Le pattern `_initialized` empêche les conflits d'initialisation.

---

### `app/routers/documents.py`

**Stockage in-memory** : `_store: dict[str, dict]` garde les `VendorDocument` en mémoire le temps du hackathon. Pas de base de données — acceptable pour une démo.

**Validation** : Vérifie que le fichier uploadé est un PDF (extension `.pdf`). Retourne 400 sinon.

---

### `data_pipeline/reference/load_reference.py`

**Script one-shot** à exécuter une seule fois pour charger les référentiels réglementaires dans le corpus RAG. Lit les 3 fichiers JSON dans `reference_data/`, formate chaque entrée en texte lisible, et les upload dans le corpus.

Les 3 sources de référence :
- **`dora_article_30.json`** : 8 exigences DORA Art. 30 avec titre, description, mots-clés, catégorie
- **`iso27001_controls.json`** : 7 contrôles ISO 27001 avec mapping vers DORA
- **`bank_rules_sample.json`** : 8 règles internes banque (RTO/RPO cibles, seuils)

---

## Explication du score RAG (cosine similarity)

Le RAG renvoie un **score de similarité cosinus** entre 0 et 1. Ce score est **mathématique**, pas un avis de Gemini.

### Comment ça fonctionne :

1. **Embedding** : Le modèle `text-multilingual-embedding-002` (768 dimensions) convertit chaque chunk de texte en un vecteur de 768 nombres. Des textes sémantiquement proches ont des vecteurs proches dans cet espace mathématique.

2. **Query** : Quand on fait `query_corpus("What is the RTO requirement?")`, la query est elle aussi convertie en vecteur.

3. **Cosine similarity** : `score = cos(θ)` où θ est l'angle entre le vecteur de la query et le vecteur du chunk. Score = 1.0 → vecteurs identiques. Score = 0.0 → vecteurs orthogonaux (aucun lien sémantique).

### Pourquoi nos scores sont bas (0.2–0.4) :

**Cause principale identifiée** : Les 24 contrats vendors sont **quasi-identiques** (taux de similarité 91.9%–98.9% entre eux — calculé avec `difflib.SequenceMatcher`). C'est le même template de contrat avec seulement le nom du prestataire qui change. Résultat :
- ~2 200 chunks de contrat presque identiques
- ~23 chunks DORA/ISO/banque (les vraies références)

Quand on requête "RTO requirement", les 2 200 chunks de contrat qui parlent tous un peu de RTO de la même façon "noient" les 23 chunks DORA qui auraient dû avoir les meilleurs scores.

**Facteurs aggravants** :
- Chunk size 800 trop grand → les chunks mélangent plusieurs sujets → vecteur "dilué"
- Certains chunks de contrat commencent par `[VendorName | category]` → le nom du vendeur dans le vecteur réduit la similarité avec des queries purement DORA
- Queries en anglais sur du texte souvent en français → perte de signal même avec un modèle multilingue

### Plan d'amélioration :
- Ne garder qu'1 contrat représentatif (pas 24 identiques)
- Réduire chunk_size à 400 pour des chunks plus précis
- Enrichir les données DORA/ISO en FR/EN (texte bilingue)
- Supprimer le préfixe `[vendor | category]` des chunks (il pollue l'embedding)

---

## Configuration (`app/config.py`)

| Variable | Valeur par défaut | Usage |
|---|---|---|
| `GCP_PROJECT` | `regagent-dora-2026` | Projet GCP |
| `GCP_REGION` | `europe-west9` | Région Gemini |
| `DOCAI_PROCESSOR_ID` | `9a4312989d6fb591` | Processor Document AI |
| `DOCAI_LOCATION` | `eu` | Multi-région Document AI |
| `DOCUMENTS_BUCKET` | `regagent-documents-eu` | Bucket GCS contrats |
| `REFERENCE_BUCKET` | `regagent-reference-eu` | Bucket GCS référence |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Modèle LLM |
| `EMBEDDING_MODEL` | `text-multilingual-embedding-002` | Modèle embeddings |
| `RAG_REGION` | `europe-west1` | Région RAG Engine |

Toutes les variables sont surchargeable par variable d'environnement.

---

## Comment lancer

### Prérequis GCP
```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project regagent-dora-2026
```

### 1. Charger les référentiels (une seule fois)
```bash
cd fintech-hackathon-2026
python3 data_pipeline/reference/load_reference.py
```

### 2. Démarrer l'API
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### 3. Uploader un contrat
```bash
curl -X POST http://localhost:8080/api/documents/upload \
  -F "file=@contrat.pdf" \
  -F "vendor_name=AWS"
```

Réponse :
```json
{
  "document_id": "a1b2c3d4",
  "vendor_name": "AWS",
  "status": "extracted",
  "total_clauses": 94,
  "total_sla_entries": 0
}
```

### 4. Requêter le corpus RAG manuellement
```python
# python3 -c depuis backend/
import sys; sys.path.insert(0, ".")
from app.services.rag_engine import get_or_create_corpus, query_corpus
corpus = get_or_create_corpus()
results = query_corpus(corpus, "RTO requirements for critical functions", top_k=5)
for r in results:
    print(round(r["score"], 3), r["text"][:120])
```

### 5. Swagger UI
```
http://localhost:8080/docs
```

---

## Dépendances clés (`requirements.txt`)

| Package | Version | Pourquoi |
|---|---|---|
| `fastapi` | ≥0.115 | Framework API async |
| `uvicorn[standard]` | ≥0.32 | Serveur ASGI |
| `google-cloud-documentai` | ≥2.32 | OCR + extraction tableaux |
| `google-cloud-aiplatform` | ≥1.74 | SDK Vertex AI (RAG Engine + Gemini) |
| `google-cloud-storage` | ≥2.19 | Upload/download GCS |
| `langchain-text-splitters` | ≥0.3 | Chunking clause-aware |
| `langchain-google-vertexai` | ≥2.0 | Intégration LangChain/Vertex |
| `pydantic` | ≥2.10 | Validation modèles de données |
| `python-multipart` | ≥0.0.18 | Parsing form-data (upload PDF) |
| `pypdf` | ≥4.0 | Split PDF > 15 pages avant Document AI |

---

## Prochaine étape : EvaluatorAgent

`app/agents/evaluator.py` — À implémenter :
1. Prend un article DORA (ex: Art. 30(2)(a) "description des services")
2. `query_corpus()` → récupère les clauses vendeur les plus proches
3. `generate()` avec le prompt `CLASSIFICATION_PROMPT` (déjà écrit dans `app/agents/prompts.py`)
4. Retourne `{status: "compliant"|"partial"|"non_compliant", score: 0.0-1.0, evidence: "..."}`

Les prompts Gemini (`CLASSIFICATION_PROMPT`, `GAP_ANALYSIS_PROMPT`) sont prêts dans `app/agents/prompts.py`.
