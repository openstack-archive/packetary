PACKAGES_SCHEMA = {
    "type": "object",
    "patternProperties": {
        "^[0-9a-z_-]+$": {
            "type": "array",
            "items":
            {
                "type": "object",
                "required": [
                    "name",
                    "versions"
                ],
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "versions": {
                        "type": "array",
                        "items": [
                            {
                                "type": "string",
                                "pattern": "^[<>=]=?\s[^\s].+$"
                            }
                        ]
                    }
                }
            }
        }
    },
    "additionalProperties": False,
}
