RPM_REPO_SCHEMA = {
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
                        ],
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "uri": {
                        "type": "string"
                    },
                    "priority": {
                        "anyOf": [
                            {
                                "type": "number",
                                        "minimum": 1,
                                        "maximum": 99,
                            },
                            {
                                "type": "null"
                            }
                        ]
                    },
                        }
            }
        }
    },
    "additionalProperties": False,
}
