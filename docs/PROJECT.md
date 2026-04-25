# RegAgent -- Projet de Documentation Complète

## Vue d'Ensemble

**RegAgent** est une plateforme multi-agents d'automatisation de la conformité DORA (Digital Operational Resilience Act) pour le secteur financier européen. Développé lors du Paris Fintech Hackathon 2026 (HEC Paris, 25-26 avril 2026), le projet transforme des documents contractuels non structurés (contrats fournisseurs, SLA, rapports SOC 2) en alertes de conformité actionnables pour les Chief Risk Officers (CRO).

**Thème du hackathon** : "Solve with AI" -- convergence entre IA générative et technologie financière.

---

## Le Problème

### Contexte réglementaire

Le règlement DORA (UE 2022/2554), pleinement applicable depuis le 17 janvier 2025, impose aux 22 000+ institutions financières européennes de prouver leur résilience opérationnelle numérique. L'enjeu central est la gestion des risques liés aux tiers (Third-Party Risk Management -- TPRM) :

- **Registre d'Information (RoI)** : chaque institution doit soumettre un inventaire exhaustif de ses fournisseurs TIC avec 15 modèles de données standardisés
- **Article 30** : exigences contractuelles détaillées (SLA, localisation, droits d'audit, sous-traitance, clauses de sortie)
- **Risque de concentration** : évaluation de la dépendance à un nombre restreint de fournisseurs

### Le goulot d'étranglement

- Un juriste met en moyenne **3,2 heures** pour examiner un seul contrat manuellement
- Lors du dry-run ESA 2024, seulement **6,5 %** des institutions ont soumis un RoI sans erreur
- Pénalités : jusqu'à **2 % du CA mondial** pour non-conformité
- Responsabilité personnelle des dirigeants : amendes jusqu'à **1 M€**

---

## La Solution RegAgent

### Proposition de valeur

RegAgent automatise l'analyse de conformité contractuelle en 3 étapes :

1. **Ingestion** : extraction automatique des clauses contractuelles depuis des PDFs
2. **Évaluation** : mapping des clauses aux exigences DORA Art. 30 et ISO 27001/27005
3. **Analyse d'écart** : comparaison avec les règles internes de la banque, génération d'alertes

### Cas d'usage principal

Un CRO télécharge un contrat fournisseur (PDF). RegAgent :
- Extrait les clauses SLA, localisation, droits d'audit, sous-traitance
- Les compare aux exigences de DORA Art. 30 et aux contrôles ISO 27001
- Les confronte aux règles internes de la banque (RTO/RPO, exigences de chiffrement)
- Génère un rapport de conformité avec score, gaps identifiés, et alertes critiques
- Produit une entrée pour le Registre d'Information

---

## Architecture Multi-Agents

RegAgent repose sur **3 agents IA spécialisés** orchestrés en séquence :

### Agent 1 -- Extractor (Extraction)

**Rôle** : ingérer les documents et en extraire les informations structurées.

- Utilise Google Document AI pour l'OCR des PDFs
- Découpe le texte en chunks sémantiques (clause-aware splitting)
- Extrait : catégorie de clause, valeurs SLA, entités, localisation géographique
- Vectorise les chunks via Vertex AI Text Embeddings

### Agent 2 -- Evaluator (Évaluation)

**Rôle** : mapper les clauses extraites aux référentiels réglementaires.

- Recherche sémantique dans l'index vectoriel (DORA + ISO)
- Classification de conformité via Gemini : `compliant`, `partial`, `non_compliant`
- Scoring de risque selon la méthodologie ISO 27005 (impact × probabilité)
- Calcul du score de concentration inter-fournisseurs

### Agent 3 -- Orchestrator (Orchestration)

**Rôle** : analyse d'écart et génération des alertes.

- Compare les garanties contractuelles aux règles internes de la banque
- Identifie les gaps (ex: RTO banque = 4h, RTO contrat = 12h → alerte critique)
- Génère des alertes avec sévérité, justification, et recommandation
- Produit les entrées du Registre d'Information (RoI) au format standardisé

### Flux de données

```
PDF Upload → Document AI (OCR) → Extractor Agent → Chunks vectorisés
                                                          ↓
Référentiel DORA/ISO (Vector Search) ← Evaluator Agent → Scores de conformité
                                                          ↓
Règles internes banque ← Orchestrator Agent → Alertes + RoI
                                                    ↓
                                            Dashboard CRO (React)
```

---

## Entité Bancaire Fictive

Pour la démonstration, RegAgent utilise un profil bancaire fictif complet :

### Eurobank Investment Solutions S.A.

| Attribut | Valeur |
|----------|--------|
| Type | Société de gestion d'actifs |
| Siège | Paris, France |
| LEI | 5493001KJTIIGC8Y1R12 |
| AUM | 47,3 Mds € |
| Employés | 342 |
| Régulateur | AMF (FR) |
| Succursales | Luxembourg, Zurich, Amsterdam |
| Groupe parent | Eurobank Group Holdings N.V. (NL) |

### 6 Fonctions Critiques

1. **Portfolio Management** -- gestion d'actifs multi-classes (RTO: 4h, RPO: 1h)
2. **Order Execution** -- exécution d'ordres (RTO: 15min, RPO: 0)
3. **Client Reporting** -- reporting réglementaire AIFMD/UCITS (RTO: 24h, RPO: 4h)
4. **Risk Monitoring** -- surveillance des risques temps réel (RTO: 30min, RPO: 15min)
5. **Client Onboarding** -- KYC/AML et due diligence (RTO: 8h, RPO: 2h)
6. **Payment Processing** -- virements et règlement-livraison (RTO: 2h, RPO: 0)

### 5 Fournisseurs TIC

| Fournisseur | Services | Coût annuel | Criticité |
|-------------|----------|-------------|-----------|
| AWS | Cloud infrastructure (IaaS) | 2 340 000 € | Critique |
| Bloomberg | Market data & analytics | 1 680 000 € | Critique |
| SWIFT | Messaging & payment network | 450 000 € | Critique |
| BlackRock Aladdin | Portfolio management platform | 3 200 000 € | Critique |
| CyberArk | PAM & identity security | 285 000 € | Important |

---

## Mapping Réglementaire

### DORA Article 30 → ISO 27001:2022

| Exigence DORA (Art. 30) | Contrôle ISO 27001 | Fonctionnalité RegAgent |
|--------------------------|-------------------|------------------------|
| Description des services TIC | A.5.19 (Relations fournisseurs) | Extraction automatique du périmètre |
| Localisation des données | A.5.23 (Sécurité cloud) | Identification géo + alerte souveraineté |
| Droits d'audit | A.5.21 (Gestion des services TIC) | Vérification clauses d'audit |
| RTO/RPO | A.5.30 (Continuité TIC) | Comparaison contractuel vs. besoins |
| Sous-traitance | A.5.21 (Chaîne fournisseurs) | Mapping chaîne de sous-traitance |
| Clauses de sortie | A.5.20 (Sécurité fournisseurs) | Vérification stratégie de sortie |
| Chiffrement | A.8.24 (Cryptographie) | Analyse des garanties crypto |

### Méthodologie de Scoring (ISO 27005)

Le score de risque combine :
- **Impact** : criticité de la fonction bancaire concernée (1-5)
- **Probabilité** : qualité des garanties contractuelles (1-5)
- **Score** = Impact × Probabilité (1-25)
- **Seuils** : ≤4 (faible), 5-9 (modéré), 10-15 (élevé), ≥16 (critique)

---

## Stack Technique

### Backend

| Composant | Technologie | Utilisation |
|-----------|------------|-------------|
| Framework | FastAPI (Python 3.12) | API REST, orchestration agents |
| LLM | Gemini 2.5 Flash (Vertex AI) | Raisonnement, classification, analyse |
| OCR | Google Document AI | Extraction texte/tables depuis PDFs |
| Embeddings | Vertex AI `text-multilingual-embedding-002` | Vectorisation des chunks |
| Vector DB | Vertex AI Vector Search | Recherche sémantique DORA/ISO |
| Storage | Google Cloud Storage | Documents uploadés + référentiel |
| Déploiement | Cloud Run | Conteneurs serverless |

### Frontend

| Composant | Technologie |
|-----------|------------|
| Framework | React 18 + TypeScript |
| Bundler | Vite |
| Build | Docker + Nginx |

### Infrastructure GCP

| Ressource | Détails |
|-----------|---------|
| Projet | `regagent-dora-2026` |
| Région | `europe-west1` (Belgium) / `europe-west9` (Paris) |
| Billing | Trial account (300$ crédits) |
| CI/CD | GitHub Actions + Workload Identity Federation |
| Registre Docker | Artifact Registry `regagent-repo` |
| Buckets GCS | `regagent-documents-eu`, `regagent-reference-eu` |
| Document AI | Processor `9a4312989d6fb591` (OCR, EU) |

---

## Structure du Projet

```
regagent-dora-2026/
├── backend/                          # API FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                   # Point d'entrée FastAPI
│       ├── config.py                 # Configuration GCP
│       ├── agents/                   # Agents IA
│       │   ├── extractor.py          # Agent extraction
│       │   ├── evaluator.py          # Agent évaluation
│       │   ├── orchestrator.py       # Agent orchestration
│       │   └── prompts.py            # Templates de prompts Gemini
│       ├── routers/                  # Endpoints API
│       │   ├── documents.py          # Upload/gestion documents
│       │   ├── analysis.py           # Analyse de conformité
│       │   ├── alerts.py             # Alertes CRO
│       │   └── register.py           # Registre d'Information
│       ├── services/                 # Services GCP
│       │   ├── document_ai.py        # Client Document AI
│       │   ├── vertex_ai.py          # Client Vertex AI (LLM + Embeddings)
│       │   ├── vector_search.py      # Client Vector Search
│       │   └── storage.py            # Client Cloud Storage
│       └── models/
│           ├── schemas.py            # Modèles Pydantic
│           └── dora_mapping.py       # Mapping DORA → ISO (statique)
├── frontend/                         # Dashboard React
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       └── components/
│           ├── Dashboard.tsx         # Vue d'ensemble CRO
│           ├── ContractUpload.tsx     # Upload de contrats
│           ├── GapAnalysis.tsx        # Analyse d'écart
│           ├── RiskMap.tsx            # Carte des risques
│           └── RegisterView.tsx       # Registre d'Information
├── data_pipeline/                    # Pipeline de données
│   ├── ingestion/
│   │   ├── extract_text.py           # Extraction Document AI
│   │   └── chunker.py               # Découpage sémantique
│   ├── vectorization/
│   │   ├── embed.py                  # Vectorisation
│   │   └── index_manager.py          # Gestion index Vector Search
│   └── reference/
│       └── load_reference.py         # Chargement référentiel
├── reference_data/                   # Données de référence
│   ├── dora_article_30.json          # Exigences DORA Art. 30
│   ├── iso27001_controls.json        # Contrôles ISO 27001
│   ├── iso27005_methodology.json     # Méthodologie de scoring
│   ├── roi_schema.json               # Schéma du Registre d'Information
│   ├── bank_entity.json              # Profil Eurobank (fictif)
│   ├── bank_functions.json           # Fonctions critiques
│   ├── bank_rules_sample.json        # Règles internes
│   ├── vendor_registry.json          # Registre fournisseurs
│   ├── concentration_matrix.json     # Matrice de concentration
│   └── vendor_contracts/             # Contrats simulés (par fournisseur)
│       ├── aws_cloud_contract.json
│       ├── bloomberg_data_contract.json
│       ├── swift_messaging_contract.json
│       ├── aladdin_platform_contract.json
│       └── cyberark_security_contract.json
├── docs/                             # Documentation
│   ├── PROJECT.md                    # Ce document
│   ├── ARCHITECTURE.md               # Architecture technique détaillée
│   ├── GETTING_STARTED.md            # Guide de démarrage
│   └── research/                     # Documents de recherche préparatoire
│       ├── Automatisation Conformité DORA...md
│       └── IA, Fintech, Risques...md
├── .github/workflows/                # CI/CD
│   ├── deploy-backend.yml
│   └── deploy-frontend.yml
├── .env.example                      # Template variables d'environnement
├── README.md                         # Vue d'ensemble rapide
└── WHAT_IS_MISSING.md                # Tâches restantes
```

---

## Registre d'Information (RoI) DORA

Le RoI est un registre standardisé exigé par les autorités de supervision. RegAgent génère automatiquement les entrées pour les 15 modèles définis par les ESAs :

| Modèle | Description | Source dans RegAgent |
|--------|-------------|---------------------|
| B_01.01 | Identification de l'entité | `bank_entity.json` |
| B_01.02 | Structure du groupe | `bank_entity.json` (group_structure) |
| B_02.01 | Arrangements contractuels | Extrait par l'Extractor Agent |
| B_03.01 | Identification des fournisseurs | `vendor_registry.json` |
| B_04.01 | Services TIC (détails) | Extrait par l'Extractor Agent |
| B_05.01 | Fonctions critiques/importantes | `bank_functions.json` |
| B_06.01 | Évaluations des risques | Produit par l'Evaluator Agent |
| B_07.01 | Sous-traitance | Extrait des contrats |

---

## Risque de Concentration

L'analyse de concentration est un pilier de DORA. RegAgent évalue :

1. **Concentration fournisseur** : dépendance à un fournisseur unique pour plusieurs fonctions critiques
2. **Concentration géographique** : exposition à une juridiction unique (ex: US, Irlande)
3. **Concentration infrastructurelle** : dépendances partagées entre fournisseurs (ex: Bloomberg et Aladdin hébergés sur AWS)
4. **Substituabilité** : capacité à remplacer un fournisseur critique (facile/modéré/difficile)

### Risques identifiés (données fictives)

- AWS : héberge 3/5 fournisseurs critiques → risque de cascade
- 4/5 fournisseurs ont des données traitées aux USA → risque juridictionnel
- Bloomberg + SWIFT : aucune alternative viable à court terme → faible substituabilité

---

## Équipe

5 ingénieurs -- Machine Learning, Cybersécurité, Architecture Web

---

## Références

- [DORA Regulation (UE 2022/2554)](https://www.digital-operational-resilience-act.com/)
- [ESA Register of Information Templates](https://www.eba.europa.eu/activities/digital-finance-and-innovation/digital-operational-resilience-act-dora)
- [ISO 27001:2022](https://www.iso.org/standard/27001)
- [ISO 27005:2022](https://www.iso.org/standard/80585.html)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Document AI Documentation](https://cloud.google.com/document-ai/docs)
