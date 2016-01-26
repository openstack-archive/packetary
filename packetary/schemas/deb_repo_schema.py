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
                        "type": "array",
                        "items":
                        {
                            "type": "string"
                        }
                    },
                }
            }
        }
    },
    "additionalProperties": False,
}
