"""
Mapping between DORA Article 30 requirements and ISO 27001:2022 controls.

Source: DORA Art. 30 key contractual provisions for ICT services
        ISO 27001:2022 Annex A controls
"""

DORA_ARTICLE_30_TO_ISO = {
    "Art. 30(2)(a)": {
        "description": "Clear and complete description of ICT services",
        "iso_control": "A.5.19",
        "iso_description": "Information security in supplier relationships",
        "check_points": [
            "Service scope definition",
            "Performance metrics",
            "Service level targets",
        ],
    },
    "Art. 30(2)(b)": {
        "description": "Data processing and storage locations",
        "iso_control": "A.5.23",
        "iso_description": "Information security for cloud services",
        "check_points": [
            "Geographic location of data centers",
            "Data sovereignty compliance",
            "Cross-border transfer restrictions",
        ],
    },
    "Art. 30(2)(c)": {
        "description": "Data protection and availability provisions",
        "iso_control": "A.5.33",
        "iso_description": "Protection of records",
        "check_points": [
            "Data encryption at rest and in transit",
            "Backup and recovery procedures",
            "Data retention policies",
        ],
    },
    "Art. 30(2)(d)": {
        "description": "Service availability, continuity, and recovery (RTO/RPO)",
        "iso_control": "A.5.30",
        "iso_description": "ICT readiness for business continuity",
        "check_points": [
            "Recovery Time Objective (RTO)",
            "Recovery Point Objective (RPO)",
            "Disaster recovery testing frequency",
        ],
    },
    "Art. 30(2)(e)": {
        "description": "Incident reporting obligations",
        "iso_control": "A.5.24",
        "iso_description": "Information security incident management planning",
        "check_points": [
            "Incident notification timeframe",
            "Severity classification",
            "Root cause analysis obligations",
        ],
    },
    "Art. 30(2)(f)": {
        "description": "Audit and inspection rights",
        "iso_control": "A.5.21",
        "iso_description": "Managing information security in ICT supply chain",
        "check_points": [
            "Right to audit clause present",
            "Audit frequency and scope",
            "Third-party audit report availability (SOC 2)",
        ],
    },
    "Art. 30(2)(g)": {
        "description": "Exit strategy and transition provisions",
        "iso_control": "A.5.20",
        "iso_description": "Addressing information security within supplier agreements",
        "check_points": [
            "Data portability guarantees",
            "Transition assistance period",
            "Data deletion after termination",
        ],
    },
    "Art. 30(3)": {
        "description": "Subcontracting chain transparency",
        "iso_control": "A.5.21",
        "iso_description": "Managing information security in ICT supply chain",
        "check_points": [
            "Subcontractor notification requirements",
            "Flow-down of security obligations",
            "Right to object to subcontractor changes",
        ],
    },
}
