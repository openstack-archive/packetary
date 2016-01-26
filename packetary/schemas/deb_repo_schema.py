DEB_REPO_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
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
        "path": {
            "type": "string"
        },
        "priority": {
            "anyOf": [
                {
                    "type": "number",
                    "minimum": 0,
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
