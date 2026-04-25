"""
Gemini prompt templates for RegAgent's three agents.

Each prompt is designed to produce structured JSON output that maps
directly to the Pydantic models in backend/app/models/schemas.py.
"""

SYSTEM_INSTRUCTION = """You are RegAgent, an expert AI compliance analyst specializing in the EU Digital Operational Resilience Act (DORA) and ISO 27001/27005 standards. You work for a European investment management company as part of the second line of defense (risk function).

Your analysis must be:
- Precise: cite specific DORA articles and ISO controls
- Structured: always respond in valid JSON
- Conservative: when in doubt, flag as non-compliant rather than compliant
- Actionable: provide clear remediation steps for each finding"""


EXTRACTION_PROMPT = """Analyze the following text extracted from a vendor ICT service contract or security report. Extract all clauses relevant to DORA Article 30 compliance.

For each relevant clause found, produce a JSON object with these fields:
- "clause_id": a unique identifier (e.g., "CL-001")
- "category": one of ["service_description", "data_residency", "data_protection", "rto_rpo", "incident_reporting", "audit_rights", "exit_strategy", "subcontracting"]
- "title": a short descriptive title
- "text": the exact clause text (verbatim or closely paraphrased)
- "dora_relevance": the DORA article this maps to (e.g., "Art. 30(2)(b)")
- "sla_values": (if applicable) extracted numeric SLA values like RTO, RPO, availability percentage
- "key_entities": any named entities (companies, locations, certifications) mentioned

If a DORA Art. 30 category is NOT covered by any clause in the document, include it in a separate "missing_categories" array.

Respond ONLY with valid JSON in this format:
{{
  "vendor_name": "<detected vendor name>",
  "document_type": "<contract/soc2_report/sla_annex/whitepaper>",
  "extracted_clauses": [...],
  "missing_categories": ["<category names not found in document>"],
  "extraction_confidence": <0.0-1.0>
}}

--- DOCUMENT TEXT ---
{document_text}
--- END DOCUMENT ---"""


CLASSIFICATION_PROMPT = """You are evaluating a vendor's contractual clause against a specific DORA/ISO requirement.

DORA/ISO REQUIREMENT:
- Article: {requirement_article}
- Title: {requirement_title}
- Requirement text: {requirement_text}
- Check points: {check_points}

VENDOR CLAUSE:
- Vendor: {vendor_name}
- Clause text: {clause_text}
- SLA values (if any): {sla_values}

TASK: Classify the vendor's compliance with this specific requirement.

Respond ONLY with valid JSON:
{{
  "requirement_article": "{requirement_article}",
  "compliance_status": "<compliant|partial|non_compliant>",
  "score": <0.0 to 1.0>,
  "evidence": "<specific text from the clause that supports your classification>",
  "gaps": ["<list of specific gaps or missing elements>"],
  "remediation": "<recommended action to achieve full compliance>"
}}

Classification guidance:
- "compliant" (score 0.8-1.0): All check points are explicitly addressed with concrete commitments
- "partial" (score 0.4-0.7): Some check points addressed but with vague language, missing specifics, or conditional commitments
- "non_compliant" (score 0.0-0.3): Requirement not addressed, explicitly excluded, or contradicted"""


GAP_ANALYSIS_PROMPT = """You are performing a Gap Analysis for DORA compliance. Compare the bank's internal requirement against the vendor's contractual guarantee.

BANK INTERNAL RULE:
- Rule ID: {rule_id}
- Category: {rule_category}
- Business Function: {rule_function}
- Criticality: {rule_criticality}
- Requirement: {rule_requirement}
{rule_specific_values}

VENDOR GUARANTEE:
- Vendor: {vendor_name}
- Contract ref: {contract_ref}
- Relevant clause: {vendor_clause_text}
- SLA values: {vendor_sla_values}

TASK: Identify the gap between what the bank requires and what the vendor guarantees.

Respond ONLY with valid JSON:
{{
  "rule_id": "{rule_id}",
  "vendor_name": "{vendor_name}",
  "gap_exists": <true|false>,
  "severity": "<critical|high|medium|low>",
  "title": "<short gap description>",
  "description": "<detailed explanation of the gap>",
  "bank_requirement_summary": "<what the bank needs>",
  "vendor_guarantee_summary": "<what the vendor offers>",
  "quantitative_gap": "<e.g., 'Bank requires RTO 4h, vendor offers RTO 12h (8h gap)'>",
  "risk_impact": "<potential business impact if this gap is not remediated>",
  "recommended_action": "<specific remediation step>",
  "dora_reference": "<relevant DORA article>"
}}

Severity classification:
- "critical": Vendor guarantee directly contradicts a critical bank requirement, or a critical DORA clause is missing entirely
- "high": Significant quantitative gap (e.g., RTO 3x worse than required) or missing guarantees for important functions
- "medium": Minor quantitative gap or vague language that could be clarified
- "low": Cosmetic issues or areas where the vendor exceeds minimum but falls short of best practice"""


ROI_GENERATION_PROMPT = """Generate a DORA Register of Information (RoI) entry for the following vendor relationship.

BANK ENTITY:
{bank_entity_json}

VENDOR DATA:
{vendor_data_json}

CONTRACT DATA:
{contract_data_json}

COMPLIANCE ASSESSMENT:
{compliance_results_json}

Generate a complete RoI entry following the EU regulatory ITS template models (B_02.01, B_02.02, B_03.01-B_03.03, B_04.01, B_05.02, B_06.01).

Respond ONLY with valid JSON:
{{
  "B_02_01": {{
    "contract_ref": "<contract reference>",
    "vendor_lei": "<LEI code>",
    "start_date": "<YYYY-MM-DD>",
    "end_date": "<YYYY-MM-DD>",
    "governing_law": "<country code>",
    "contract_type": "<outsourcing|procurement|partnership>"
  }},
  "B_02_02": [
    {{
      "contract_ref": "<contract reference>",
      "function_id": "<function ID>",
      "is_critical": <true|false>,
      "substitutability": "<easy|difficult|impossible>"
    }}
  ],
  "B_03_01": {{
    "provider_lei": "<LEI>",
    "provider_name": "<legal name>",
    "provider_country": "<country code>",
    "is_intragroup": <true|false>
  }},
  "B_03_03": [
    {{
      "service_id": "<service ID>",
      "function_id": "<function ID>",
      "data_location": "<region/country>"
    }}
  ],
  "B_04_01": [
    {{
      "subcontractor_lei": "<LEI>",
      "subcontractor_name": "<name>",
      "service_provided": "<description>",
      "data_location": "<region>"
    }}
  ],
  "B_06_01": {{
    "overall_criticality": "<critical|important|standard>",
    "impact_assessment": "<description of disruption impact>",
    "substitutability_assessment": "<description of vendor replaceability>",
    "compliance_score": <0.0-1.0>
  }}
}}"""


CONCENTRATION_RISK_PROMPT = """Analyze the concentration risk for the following vendor portfolio.

VENDOR REGISTRY:
{vendor_registry_json}

DEPENDENCY MATRIX:
{concentration_matrix_json}

BANK FUNCTIONS:
{bank_functions_json}

TASK: Identify concentration risks across the vendor portfolio.

For each risk identified, provide:
1. The shared infrastructure or dependency
2. Which vendors are affected
3. Which business functions would be impacted
4. Substitutability assessment
5. Recommended mitigation

Respond ONLY with valid JSON:
{{
  "concentration_risks": [
    {{
      "risk_id": "<unique ID>",
      "risk_type": "<infrastructure|geographic|vendor|technology>",
      "severity": "<critical|high|medium|low>",
      "description": "<detailed risk description>",
      "shared_dependency": "<what is shared>",
      "affected_vendors": ["<vendor names>"],
      "affected_functions": ["<function IDs>"],
      "impact_scenario": "<what happens if the shared dependency fails>",
      "substitutability": "<easy|difficult|impossible>",
      "mitigation": "<recommended action>"
    }}
  ],
  "overall_concentration_score": <0.0-1.0>,
  "summary": "<1-2 sentence executive summary for the CRO>"
}}"""
