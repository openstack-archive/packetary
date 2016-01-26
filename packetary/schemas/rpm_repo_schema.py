RPM_REPO_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
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
        "path": {
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
