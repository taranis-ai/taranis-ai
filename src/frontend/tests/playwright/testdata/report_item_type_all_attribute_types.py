# Uses only Attribute.name values that exist in your /config/attributes payload:
# Story, Text, Number, Boolean, Confidentiality (RADIO), Impact (ENUM),
# Text Area, Rich Text, Date, Time, Date Time, TLP,
# Link, Attachment, CPE, CVE, CVSS

report_definition: dict = {
    "title": "Zzz_All Attribute Types Report",
    "description": "One field per AttributeType, referencing existing seeded Attributes by name.",
    "attribute_groups": [
        {
            "title": "Overview",
            "description": "Primitive + choice + story",
            "index": 0,
            "attribute_group_items": [
                {
                    "title": "Related Story",
                    "description": "STORY field",
                    "index": 0,
                    "attribute": "Story",  # AttributeType.STORY
                },
                {
                    "title": "Text (String)",
                    "description": "STRING field",
                    "index": 1,
                    "attribute": "Text",  # AttributeType.STRING
                },
                {
                    "title": "Number",
                    "description": "NUMBER field",
                    "index": 2,
                    "attribute": "Number",  # AttributeType.NUMBER
                },
                {
                    "title": "Boolean",
                    "description": "BOOLEAN field",
                    "index": 3,
                    "attribute": "Boolean",  # AttributeType.BOOLEAN
                },
                {
                    "title": "Confidentiality (Radio)",
                    "description": "RADIO field",
                    "index": 4,
                    "attribute": "Confidentiality",  # AttributeType.RADIO
                },
                {
                    "title": "Impact (Enum)",
                    "description": "ENUM field",
                    "index": 5,
                    "attribute": "Impact",  # AttributeType.ENUM
                },
            ],
        },
        {
            "title": "Narrative and Timing",
            "description": "Text fields and time-related attributes",
            "index": 1,
            "attribute_group_items": [
                {
                    "title": "Text Area",
                    "description": "TEXT field",
                    "index": 0,
                    "attribute": "Text Area",  # AttributeType.TEXT
                },
                {
                    "title": "Rich Text",
                    "description": "RICH_TEXT field",
                    "index": 1,
                    "attribute": "Rich Text",  # AttributeType.RICH_TEXT
                },
                {
                    "title": "Date",
                    "description": "DATE field",
                    "index": 2,
                    "attribute": "Date",  # AttributeType.DATE
                },
                {
                    "title": "Time",
                    "description": "TIME field",
                    "index": 3,
                    "attribute": "Time",  # AttributeType.TIME
                },
                {
                    "title": "Date Time",
                    "description": "DATE_TIME field",
                    "index": 4,
                    "attribute": "Date Time",  # AttributeType.DATE_TIME
                },
                {
                    "title": "TLP",
                    "description": "TLP field",
                    "index": 5,
                    "attribute": "TLP",  # AttributeType.TLP
                },
            ],
        },
        {
            "title": "Technical References and Artifacts",
            "description": "Links, attachments, and security-specific dictionary fields",
            "index": 2,
            "attribute_group_items": [
                {
                    "title": "Link",
                    "description": "LINK field",
                    "index": 0,
                    "attribute": "Link",  # AttributeType.LINK
                },
                {
                    "title": "Attachment",
                    "description": "ATTACHMENT field",
                    "index": 1,
                    "attribute": "Attachment",  # AttributeType.ATTACHMENT
                },
                {
                    "title": "CPE",
                    "description": "CPE field",
                    "index": 2,
                    "attribute": "CPE",  # AttributeType.CPE
                },
                {
                    "title": "CVE",
                    "description": "CVE field",
                    "index": 3,
                    "attribute": "CVE",  # AttributeType.CVE
                },
                {
                    "title": "CVSS",
                    "description": "CVSS field",
                    "index": 4,
                    "attribute": "CVSS",  # AttributeType.CVSS
                },
            ],
        },
    ],
}
