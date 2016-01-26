DEB_REPO_SCHEMA = {
    "type": "object",
    "patternProperties": {
        "^[0-9a-z_-]+$": {
            "type": "array",
            "items":
            {
                "type": "object",
                "required": [
                    "name",
                    "uri",
                    "suite",
                    "section"
                ],
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "type": {
                        "type": "string",
                                "enum": ["deb"]
                    },
                    "uri": {
                        "type": "string"
                    },
                    "priority": {
                        "anyOf": [
                            {
                                "type": "number",
                                        "minimum": 0,
                                        "maximum": 1000,
                            },
                            {
                                "type": "null"
                            }
                        ]
                    },
                    "suite": {
                        "type": "string"
                    },
                    "section": {
                        "type": "string"
                    },
                }
            }
        }
    },
    "additionalProperties": False,
}
