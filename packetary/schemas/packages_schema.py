PACKAGES_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "array",
    "items": {
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
                                "pattern": "^[<>=]=?\s[^\s]+$"
                    }
                ]
            }
        }
    }
}
