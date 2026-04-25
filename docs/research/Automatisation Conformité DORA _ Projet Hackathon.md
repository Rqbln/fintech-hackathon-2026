# **Vers une Résilience Opérationnelle Automatisée : Analyse Stratégique et Technique du Projet RegAgent pour la Conformité DORA**

## **L'Émergence de la Compliance Tech : Un Nouveau Paradigme pour le Secteur Financier Européen**

Le paysage financier européen traverse une mutation structurelle profonde, marquée par un déplacement du centre de gravité de la régulation. Traditionnellement axée sur la solvabilité financière et la gestion des risques de marché, la surveillance réglementaire se concentre désormais sur la résilience opérationnelle numérique. Ce changement de paradigme est incarné par le règlement sur la résilience opérationnelle numérique (Digital Operational Resilience Act, ou DORA), entré en vigueur en janvier 2023 et devenu pleinement applicable le 17 janvier 2025\.1 Dans ce contexte, l'entretien avec Julien Garnier a permis de cristalliser une vision stratégique essentielle : la "Compliance Tech" n'est plus une fonction support, mais la priorité absolue pour l'innovation fintech contemporaine.

L'analyse de Julien Garnier souligne que l'innovation dans la fintech grand public s'essouffle face à la maturité des marchés, tandis que la conformité technologique représente un "océan bleu" de croissance. Le verdict est sans appel : automatiser la conformité, et plus spécifiquement le cadre DORA, constitue l'opportunité commerciale la plus pertinente du moment. Cette orientation impose toutefois l'abandon de certaines pistes technologiques jugées inefficaces par l'industrie, notamment les chatbots financiers, qui ne répondent pas aux besoins de complexité de la banque privée ni à la simplicité des services de détail, et l'EU AI Act, dont l'urgence opérationnelle est actuellement jugée secondaire par rapport à la pression immédiate de DORA.3

Le projet RegAgent se positionne précisément à l'intersection de cette urgence réglementaire et de la nécessité d'efficience opérationnelle. Il s'agit de transformer une contrainte juridique massive en un avantage stratégique grâce à l'intelligence artificielle localisée. Pour le secteur financier, l'enjeu n'est pas seulement d'éviter des amendes pouvant atteindre 2 % du chiffre d'affaires mondial, mais de sécuriser l'intégralité d'une chaîne de valeur devenue intrinsèquement dépendante de prestataires technologiques tiers.2

## **Quantification du Problème : L'Impasse de la Gestion Manuelle de la Conformité**

L'ampleur du défi posé par DORA peut être quantifiée par le volume d'entités concernées et la complexité des exigences de reporting. Plus de 22 000 institutions financières et prestataires de services de technologie de l'information et de la communication (TIC) au sein de l'Union européenne tombent sous le coup de cette réglementation.5 Pour ces acteurs, le passage d'une gestion des risques basée sur des feuilles de calcul à un cadre de résilience dynamique représente un saut qualitatif et financier colossal.

### **Les Coûts de la Mise en Conformité et de la Non-Conformité**

Les investissements nécessaires pour atteindre la conformité DORA sont massifs. Les grandes institutions financières prévoient des budgets allant de 25 à 150 millions d'euros pour la mise en œuvre complète, dont 5 à 15 millions sont consacrés uniquement à la phase de stratégie et de planification.3 En moyenne, le coût par employé pour une banque de taille moyenne est estimé à environ 10 000 dollars par an pour maintenir ces standards.3

| Catégorie d'Entité | Budget de Planification | Coût de Mise en Œuvre Totale | Risque de Pénalité (Max) |
| :---- | :---- | :---- | :---- |
| Grande Banque Systémique | €5M – €15M | €100M+ | 2% du CA mondial |
| Institution Financière Moyenne | €2M – €5M | €10M – €25M | €40M (ex. pour 2Md€ CA) |
| Prestataire TIC Critique | N/A | Variable | 1% du CA journalier moyen |

Données consolidées à partir des sources : 2

Le coût de la non-conformité ne se limite pas aux amendes. La responsabilité personnelle des dirigeants est désormais engagée, avec des amendes pouvant atteindre 1 million d'euros pour les manquements graves.2 De plus, 90 % des violations dans le secteur financier sont motivées par le gain financier, et le coût moyen d'une faille de données s'élève à 5,56 millions de dollars.4 L'absence de vision claire sur les dépendances vis-à-vis des tiers multiplie ces risques par l'effet de cascade.

### **Le Goulot d'Étranglement des Contrats Tiers**

Le cœur du problème identifié par Julien Garnier réside dans l'exploitation des données non structurées provenant des fournisseurs TIC. Actuellement, les équipes de conformité doivent traiter manuellement des milliers de documents contractuels, des descriptions de niveaux de service (SLA) et des rapports d'audit tiers. Un juriste ou un analyste de risque passe en moyenne 3,2 heures pour examiner un seul contrat manuellement.10 Pour une banque gérant 1 000 contrats, cela représente 3 200 heures de travail hautement qualifié, souvent sujet à l'erreur humaine due à la fatigue.12

L'exercice "Dry Run" mené par les autorités européennes (ESAs) en 2024 a révélé que seulement 6,5 % des institutions financières ont réussi à soumettre un "Registre d'Information" exempt d'erreurs de qualité de données.14 La majorité des échecs sont dus à des codes d'identification incorrects (LEI) et à une incapacité à relier correctement les contrats aux fonctions critiques de l'entreprise.14 Ce constat valide l'urgence d'un outil comme RegAgent capable de structurer automatiquement ces données.

## **Analyse Approfondie de la Solution : Le Projet RegAgent**

Le projet RegAgent n'est pas un simple outil de gestion documentaire, mais un moteur d'intelligence juridique et technique conçu pour automatiser l'analyse de risque liée aux tiers. Sa mission est de transformer des "monceaux de documents non structurés" en un graphe de connaissances actionnable, aligné sur les règles de résilience internes de la banque.

### **Architecture Fonctionnelle : Ingestion, Classification et Mapping**

La solution repose sur un flux de travail en trois étapes critiques, directement inspiré des besoins opérationnels du terrain.

**1\. Ingestion et Analyse à l'Échelle** L'outil doit être capable d'absorber des documents hétérogènes (PDF scannés, contrats Word, annexes techniques) et d'en extraire la substantifique moelle. L'utilisation de Mistral OCR est ici centrale, car elle permet de capturer non seulement le texte, mais aussi la structure logique des documents, comme les tableaux de SLA ou les schémas de sous-traitance.16 Contrairement à une recherche textuelle classique, le système identifie les concepts juridiques et techniques (ex: temps de rétention, localisation des données, clauses de sortie) indépendamment de leur formulation spécifique.17

**2\. Classification et Normalisation des Garanties** Une fois les données extraites, RegAgent les catégorise selon un référentiel prédéfini. Par exemple, une clause relative à la "reprise après sinistre" est automatiquement "mappée" aux exigences de l'Article 30 de DORA concernant la continuité des activités.19 Le système attribue un score de conformité à chaque garantie fournie par le prestataire par rapport aux standards du marché.

**3\. Reflet des Règles Internes et Analyse d'Écart (Gap Analysis)** C'est ici que réside la véritable valeur ajoutée pour le jury du hackathon. RegAgent ne se contente pas de lire le contrat ; il le compare à la stratégie de résilience de la banque. Si la banque a défini un Objectif de Temps de Restauration (RTO) de 4 heures pour ses services de paiement, mais que le contrat du fournisseur de cloud stipule un RTO de 12 heures, l'IA doit lever une alerte critique immédiatement.21

### **Alignement avec les Référentiels ISO 27001 et ISO 27005**

Comme suggéré par Julien Garnier, RegAgent s'appuie sur des normes établies pour définir son cadre d'analyse de risque. Cette approche garantit que l'outil est "auditable" et compatible avec les systèmes de gestion de la sécurité de l'information (ISMS) existants.24

| Exigence DORA (Art. 30\) | Contrôle ISO 27001:2022 | Fonctionnalité RegAgent |
| :---- | :---- | :---- |
| Description des services TIC | A.5.19 (Relations fournisseurs) | Extraction automatique de la portée du service |
| Localisation du stockage des données | A.5.23 (Sécurité cloud) | Identification géographique et alerte de souveraineté |
| Droits d'audit et d'inspection | A.5.21 (Gestion des services) | Vérification de la présence des clauses d'audit |
| Objectifs de récupération (RTO/RPO) | A.5.30 (Continuité TIC) | Comparaison contractuelle vs. besoins business |

Source : 25

En intégrant la méthodologie de l'ISO 27005, RegAgent évalue le risque en combinant l'importance de l'actif (la fonction bancaire) avec la vulnérabilité du contrat (les lacunes dans les garanties du fournisseur).24 Cela permet de prioriser les renégociations contractuelles là où l'impact potentiel d'une cyberattaque serait le plus dévastateur.

## **Méthodologie Hackathon : Construction du Moteur d'IA**

Pour démontrer la pertinence du projet lors d'un hackathon, il est impératif de suivre une feuille de route rigoureuse qui transforme la théorie réglementaire en démonstration technique.

### **Étape 1 : Définition du Référentiel de Risque**

L'IA ne peut fonctionner dans un vide sémantique. La première étape consiste à injecter dans le système les connaissances issues des normes ISO 27001 et 27005, ainsi que les exigences spécifiques de DORA.24 Ce référentiel sert de base à la création d'un "modèle de données de conformité". Pour le hackathon, cela peut être représenté par un schéma JSON décrivant les 15 modèles du Registre d'Information (RoI) exigé par les autorités européennes.23

### **Étape 2 : Cartographie de l'Entité Business**

RegAgent doit permettre à l'utilisateur de définir le périmètre critique de la banque. Il s'agit d'identifier les fonctions "essentielles" au sens de DORA : celles dont l'interruption compromettrait la stabilité financière ou la continuité des services.8 L'interface de l'outil doit permettre de lier ces fonctions aux systèmes informatiques correspondants, créant ainsi une hiérarchie de criticité.

### **Étape 3 : Confrontation Systèmes/Enjeux**

Le moteur de RegAgent exécute alors une analyse de cohérence. Si le système identifie qu'un service de sécurité tiers est crucial pour une fonction ne supportant aucune perte de données (RPO \= 0), il va chercher dans les contrats et les rapports SOC 2 du fournisseur si les mécanismes de réplication synchrone sont effectivement garantis.22 Cette étape transforme l'IA d'un simple extracteur de texte en un véritable conseiller en gestion des risques.

## **Stack Technique : Performance, Confidentialité et Localisation**

La stratégie technique est dictée par une contrainte absolue de sécurité des données. Les contrats bancaires étant hautement confidentiels, aucune donnée ne doit quitter l'infrastructure de la banque vers des API cloud tierces.32

### **Composants Clés de la Stack**

* **Extraction Documentaire : Mistral OCR.** Ce modèle est optimisé pour les PDF complexes. Il permet d'extraire les métadonnées structurées et de maintenir le contexte spatial des clauses, ce qui est crucial pour prouver l'emplacement d'une signature ou d'une annexe technique.16  
* **Moteur d'IA : Mistral Large 2 (ou Mistral 7B pour la rapidité).** Déployé localement, ce modèle servira à la classification et au raisonnement juridique. Sa capacité multilingue est essentielle pour traiter des contrats de fournisseurs paneuropéens.35  
* **Orchestration : vLLM.** Pour garantir une haute performance et une faible latence lors de l'analyse de gros volumes de documents, vLLM offre un débit nettement supérieur aux solutions classiques comme Ollama, permettant de traiter des centaines de pages par minute.35  
* **Base de Données Vectorielle : PGVector (PostgreSQL).** Elle permet de stocker les "embeddings" des contrats et du référentiel ISO, facilitant la recherche sémantique par similarité sans exposer les données à des vecteurs d'attaque cloud.33  
* **Pipeline RAG (Retrieval-Augmented Generation) Local.** Le système utilise une architecture RAG "air-gapped" (sans connexion internet). Les documents sont découpés en morceaux (chunks), indexés, puis récupérés par l'IA pour répondre à des questions spécifiques sur la conformité.32

### **Dimensionnement Hardware pour le Hackathon**

Pour faire tourner cette stack de manière fluide, une configuration robuste est nécessaire :

* **GPU :** Au moins une NVIDIA RTX 4090 (24 Go VRAM) pour le modèle 7B ou une A100/H100 pour Mistral Large 2 en quantification 4-bit.35  
* **RAM :** 64 Go minimum pour gérer le chargement des modèles et la base de données vectorielle.  
* **Stockage :** SSD NVMe rapide pour l'indexation et la récupération instantanée des documents.

## **Potentiel Commercial et Scalabilité : Un Marché Européen en Attente**

La vision de Julien Garnier sur le potentiel de création d'entreprise est étayée par des données de marché solides. Le problème de la conformité DORA n'est pas limité à un seul pays ou à un seul type d'acteur.

### **Un Marché Total Adressable (TAM) Massif**

Avec plus de 22 000 entités régulées, le marché des solutions de conformité DORA est estimé à plusieurs milliards d'euros par an. Les institutions financières cherchent désespérément à réduire leurs coûts opérationnels tout en minimisant les risques de sanctions.

| Segment de Marché | Besoins Spécifiques | Potentiel de Scalabilité |
| :---- | :---- | :---- |
| Banques et Assurances | Registre d'Information, Audit fournisseurs | Très élevé (Standardisation européenne) |
| Fintechs et Paiements | Due diligence rapide, résilience agile | Élevé (Besoin d'automatisation) |
| Prestataires TIC (GCP, Azure, etc.) | Preuve de conformité pour leurs clients | Modéré (Outils internes) |

Données basées sur : 3

### **L'Automatisation comme Levier de Rentabilité (ROI)**

L'implémentation de RegAgent peut générer des économies spectaculaires. En réduisant le temps de revue contractuelle de 82 %, une institution peut économiser des centaines de milliers d'euros en frais de personnel et en honoraires juridiques externes dès la première année.40 De plus, l'outil permet d'éliminer 94 % des violations de conformité "évitables" liées à des erreurs humaines de saisie de données.40

La scalabilité de RegAgent repose sur sa capacité à s'adapter aux différents régulateurs nationaux (NCAs) via des modèles de reporting standardisés (xBRL-CSV), tout en restant flexible face aux évolutions futures de la réglementation grâce à son architecture basée sur des modèles de langage généralistes performants.30

## **Recommandations pour la Présentation au Jury**

Pour maximiser l'impact auprès du jury du hackathon, le projet doit mettre en avant trois piliers : la douleur du client, la robustesse technique et la pertinence réglementaire.

**1\. Souligner l'Urgence Opérationnelle** Le jury doit comprendre que DORA n'est pas une lointaine promesse, mais une réalité quotidienne qui "brise" la santé mentale des équipes de sécurité et pèse sur les bilans financiers.8 RegAgent n'est pas un gadget, c'est un remède à la surcharge informationnelle.

**2\. Démontrer la Maîtrise du Framework ISO/DORA** Il est crucial de montrer que l'IA ne fait pas que du "text matching". Elle comprend les concepts de RTO, RPO, de concentration de risque et de cascade de sous-traitance.29 La présentation d'un tableau de correspondance entre un contrat réel et les exigences de l'Article 30 sera une preuve de concept puissante.

**3\. Garantir la Souveraineté des Données** Dans le secteur bancaire, l'argument de l'IA locale est l'argument massue. En utilisant les modèles de Mistral AI déployés sur site, RegAgent lève le principal frein à l'adoption de l'IA générative dans les départements juridiques et de conformité.33

En conclusion, RegAgent incarne la "Compliance Tech" de demain : intelligente, souveraine et profondément ancrée dans les réalités métier. C'est un projet qui ne se contente pas de résoudre un problème technique, mais qui sécurise l'infrastructure même du système financier européen face aux défis de l'ère numérique.

#### **Sources des citations**

1. Digital Operational Resilience Act (DORA) \- | European Securities and Markets Authority, consulté le avril 21, 2026, [https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/digital-operational-resilience-act-dora](https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/digital-operational-resilience-act-dora)  
2. DORA Has Been Mandatory Since January: Why Two-Thirds of Financial Firms Fall Short, consulté le avril 21, 2026, [https://www.digital-chiefs.de/en/dora-mandatory-january-financial-firms-compliance/](https://www.digital-chiefs.de/en/dora-mandatory-january-financial-firms-compliance/)  
3. How Much Does a DORA Certification Cost? \- Centraleyes, consulté le avril 21, 2026, [https://www.centraleyes.com/how-much-does-a-dora-certification-cost/](https://www.centraleyes.com/how-much-does-a-dora-certification-cost/)  
4. Filigran Report: 90% of Financial Sector Breaches Driven by Financial Gain as AI and Supply Chain Threats Escalate | Morningstar, consulté le avril 21, 2026, [https://www.morningstar.com/news/business-wire/20260421513542/filigran-report-90-of-financial-sector-breaches-driven-by-financial-gain-as-ai-and-supply-chain-threats-escalate](https://www.morningstar.com/news/business-wire/20260421513542/filigran-report-90-of-financial-sector-breaches-driven-by-financial-gain-as-ai-and-supply-chain-threats-escalate)  
5. Learn About the EU's DORA Financial Regulation \- Fortra, consulté le avril 21, 2026, [https://www.fortra.com/blog/learn-about-eus-dora-financial-regulation](https://www.fortra.com/blog/learn-about-eus-dora-financial-regulation)  
6. DORA and its impact on UK financial entities and ICT service providers \- PwC UK, consulté le avril 21, 2026, [https://www.pwc.co.uk/industries/financial-services/insights/dora-and-its-impact-on-uk-financial-entities-and-ict-service-providers.html](https://www.pwc.co.uk/industries/financial-services/insights/dora-and-its-impact-on-uk-financial-entities-and-ict-service-providers.html)  
7. Understanding the DORA regulation: Europe's strategy for a more digitally resilient financial sector \- Deepki, consulté le avril 21, 2026, [https://www.deepki.com/blog/dora-regulation-resilient-financial-sector/](https://www.deepki.com/blog/dora-regulation-resilient-financial-sector/)  
8. DORA Compliance Requirements for Financial Institutions | 2025 Guide \- Dotfile, consulté le avril 21, 2026, [https://www.dotfile.com/resources/dora-compliance-requirements-for-financial-institutions-2025-guide](https://www.dotfile.com/resources/dora-compliance-requirements-for-financial-institutions-2025-guide)  
9. DORA Compliance Cost Calculator \- Estimate Your Implementation Budget, consulté le avril 21, 2026, [https://www.regulation-dora.eu/tools/compliance-cost-calculator](https://www.regulation-dora.eu/tools/compliance-cost-calculator)  
10. How to Review Contracts? Complete Contract Review Process \- HyperStart CLM, consulté le avril 21, 2026, [https://www.hyperstart.com/blog/contract-review/](https://www.hyperstart.com/blog/contract-review/)  
11. Business case for contract review AI tool – how to estimate value? : r/legaltech \- Reddit, consulté le avril 21, 2026, [https://www.reddit.com/r/legaltech/comments/1mz1xq9/business\_case\_for\_contract\_review\_ai\_tool\_how\_to/](https://www.reddit.com/r/legaltech/comments/1mz1xq9/business_case_for_contract_review_ai_tool_how_to/)  
12. AI vs. Manual Legal Contract Review: A Comparison Guide for Modern Legal Teams, consulté le avril 21, 2026, [https://www.spellbook.legal/learn/ai-vs-manual-legal-contract-review](https://www.spellbook.legal/learn/ai-vs-manual-legal-contract-review)  
13. The Ultimate Guide to Contract Review in 2026 \- TermScout Blog, consulté le avril 21, 2026, [https://blog.termscout.com/the-ultimate-guide-to-contract-review-in-2026](https://blog.termscout.com/the-ultimate-guide-to-contract-review-in-2026)  
14. ESAs workshop on DORA dry run lessons learnt and data quality \- European Banking Authority, consulté le avril 21, 2026, [https://www.eba.europa.eu/sites/default/files/2024-12/7d38950b-c20f-4865-a2e2-e9f8a342996d/2024\_12\_18\_dora\_dry\_run\_summary\_workshop\_-\_final.pdf](https://www.eba.europa.eu/sites/default/files/2024-12/7d38950b-c20f-4865-a2e2-e9f8a342996d/2024_12_18_dora_dry_run_summary_workshop_-_final.pdf)  
15. ESA DORA dry run exercise summary report | Global Regulation Tomorrow, consulté le avril 21, 2026, [https://www.regulationtomorrow.com/2024/12/esa-dora-dry-run-exercise-summary-report/](https://www.regulationtomorrow.com/2024/12/esa-dora-dry-run-exercise-summary-report/)  
16. Mistral OCR, consulté le avril 21, 2026, [https://mistral.ai/news/mistral-ocr](https://mistral.ai/news/mistral-ocr)  
17. DORA Article 30: Key contractual provisions \- Advisera, consulté le avril 21, 2026, [https://advisera.com/dora-regulation/key-contractual-provisions/](https://advisera.com/dora-regulation/key-contractual-provisions/)  
18. Dora Mapping \- GoTo, consulté le avril 21, 2026, [https://www.goto.com/company/legal/dora-mapping](https://www.goto.com/company/legal/dora-mapping)  
19. Digital Operational Resilience Act (DORA), Article 30, consulté le avril 21, 2026, [https://www.digital-operational-resilience-act.com/Article\_30.html](https://www.digital-operational-resilience-act.com/Article_30.html)  
20. Digital Operational Resilience Act (DORA) Article 30 – Key contractual provisions \- Securiti, consulté le avril 21, 2026, [https://securiti.ai/dora-article-30/](https://securiti.ai/dora-article-30/)  
21. DORA: the regulation reshaping digital resilience in the European financial sector, consulté le avril 21, 2026, [https://www.cosmikal.es/dora-the-regulation-reshaping-digital-resilience-in-the-european-financial-sector/](https://www.cosmikal.es/dora-the-regulation-reshaping-digital-resilience-in-the-european-financial-sector/)  
22. Digital Operational Experience Act (DORA) \- LogicMonitor, consulté le avril 21, 2026, [https://www.logicmonitor.com/legal/digital-operational-resilience-act](https://www.logicmonitor.com/legal/digital-operational-resilience-act)  
23. DORA Register of Information (RoI) Template Download \- Official ..., consulté le avril 21, 2026, [https://vendorica.com/supervisory/register-of-information/template/](https://vendorica.com/supervisory/register-of-information/template/)  
24. ISO 27001 Risk Assessment, Treatment, & Management: The Complete Guide \- Advisera, consulté le avril 21, 2026, [https://advisera.com/27001academy/iso-27001-risk-assessment-treatment-management/](https://advisera.com/27001academy/iso-27001-risk-assessment-treatment-management/)  
25. DORA ISO 27001 mapping: turning compliance into resilience \- Copla, consulté le avril 21, 2026, [https://copla.com/blog/compliance-regulations/dora-iso-27001-mapping-turning-compliance-into-resilience/](https://copla.com/blog/compliance-regulations/dora-iso-27001-mapping-turning-compliance-into-resilience/)  
26. ICF including ISO & DORA mapping \- Exact, consulté le avril 21, 2026, [https://files.exact.com/static/downloads/information-security/ICF%20including%20ISO%20&%20DORA%20mapping.pdf](https://files.exact.com/static/downloads/information-security/ICF%20including%20ISO%20&%20DORA%20mapping.pdf)  
27. The 5 Pillars of DORA Explained – Building Digital Resilience in Financial Services, consulté le avril 21, 2026, [https://www.surecloud.com/blog-hub/five-pillars-of-dora-explained](https://www.surecloud.com/blog-hub/five-pillars-of-dora-explained)  
28. ISO 27001 Controls Ultimate Guide \- High Table, consulté le avril 21, 2026, [https://hightable.io/iso-27001-controls/](https://hightable.io/iso-27001-controls/)  
29. DORA Third-Party Risk Management Compliance | Prevalent \- Mitratech, consulté le avril 21, 2026, [https://mitratech.com/resource-hub/rc-use-case/eu-digital-operational-resilience-act-compliance/](https://mitratech.com/resource-hub/rc-use-case/eu-digital-operational-resilience-act-compliance/)  
30. DORA Reporting: 5 Surprising Lessons from Europe's Biggest Regulatory Dry Run, consulté le avril 21, 2026, [https://fund-xp.lu/dora/dora-reporting/](https://fund-xp.lu/dora/dora-reporting/)  
31. Critical or Important Functions Under DORA | Proofpoint US, consulté le avril 21, 2026, [https://www.proofpoint.com/us/legal/trust/critical-or-important-functions-under-dora](https://www.proofpoint.com/us/legal/trust/critical-or-important-functions-under-dora)  
32. Private RAG Deployment: Building Zero-Leakage Retrieval Pipelines for Enterprise, consulté le avril 21, 2026, [https://blog.premai.io/private-rag-deployment-guide/](https://blog.premai.io/private-rag-deployment-guide/)  
33. Privacy-Preserving AI: My Journey to a Self-Hosted RAG Pipeline | by M. Habib | DKatalis | Apr, 2026 | Medium, consulté le avril 21, 2026, [https://medium.com/dkatalis/privacy-preserving-ai-my-journey-to-a-self-hosted-rag-pipeline-085a1e1f5d7a](https://medium.com/dkatalis/privacy-preserving-ai-my-journey-to-a-self-hosted-rag-pipeline-085a1e1f5d7a)  
34. A Privacy-First Architecture for Fully Local Retrieval-Augmented Generation in Secure Document Intelligence \- TechRxiv, consulté le avril 21, 2026, [https://www.techrxiv.org/doi/pdf/10.36227/techrxiv.176800894.46972585/v1?onload=true](https://www.techrxiv.org/doi/pdf/10.36227/techrxiv.176800894.46972585/v1?onload=true)  
35. Self-Hosted LLM Guide: Setup, Tools & Cost Comparison (2026) \- Prem AI, consulté le avril 21, 2026, [https://blog.premai.io/self-hosted-llm-guide-setup-tools-cost-comparison-2026/](https://blog.premai.io/self-hosted-llm-guide-setup-tools-cost-comparison-2026/)  
36. Local LLM Deployment: Privacy-First AI Complete Guide \- Digital Applied, consulté le avril 21, 2026, [https://www.digitalapplied.com/blog/local-llm-deployment-privacy-guide-2025](https://www.digitalapplied.com/blog/local-llm-deployment-privacy-guide-2025)  
37. Build a Self-Hosted OpenAI-Compatible API with vLLM in 2026 | Spheron Blog, consulté le avril 21, 2026, [https://www.spheron.network/blog/openai-compatible-api-self-hosted/](https://www.spheron.network/blog/openai-compatible-api-self-hosted/)  
38. RAG Basics with Mistral AI, consulté le avril 21, 2026, [https://docs.mistral.ai/resources/cookbooks/mistral-rag-basic\_rag](https://docs.mistral.ai/resources/cookbooks/mistral-rag-basic_rag)  
39. Evaluating RAG with LLM as a Judge | Mistral AI, consulté le avril 21, 2026, [https://mistral.ai/news/llm-as-rag-judge](https://mistral.ai/news/llm-as-rag-judge)  
40. Compliance Automation ROI — What Manual Tracking Costs \- FileFlo, consulté le avril 21, 2026, [https://www.getfileflo.com/blog/compliance-automation-roi](https://www.getfileflo.com/blog/compliance-automation-roi)  
41. The Real ROI of Contract Management Software: A CFO's Guide \- Webflow Ecommerce website template \- Pakta, consulté le avril 21, 2026, [https://www.pakta.app/blogs/the-real-roi-of-contract-management-software-a-cfos-guide](https://www.pakta.app/blogs/the-real-roi-of-contract-management-software-a-cfos-guide)  
42. Association for Financial Markets in Europe Position Paper DORA Register of Information: Implementation Lessons and Future Princ \- AFME, consulté le avril 21, 2026, [https://www.afme.eu/media/egqfikb1/dora-registers-of-information\_afme-final.pdf](https://www.afme.eu/media/egqfikb1/dora-registers-of-information_afme-final.pdf)  
43. DORA \- Rubrik, consulté le avril 21, 2026, [https://www.rubrik.com/content/dam/rubrik/en/resources/report-review/rpt-rzl-emea-finance-edition.pdf](https://www.rubrik.com/content/dam/rubrik/en/resources/report-review/rpt-rzl-emea-finance-edition.pdf)  
44. DORA – Managing of ICT third-party risk \- FMA Österreich, consulté le avril 21, 2026, [https://www.fma.gv.at/en/cross-sectoral-topics/dora/dora-managing-of-ict-third-party-risk/](https://www.fma.gv.at/en/cross-sectoral-topics/dora/dora-managing-of-ict-third-party-risk/)