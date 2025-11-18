
SQL_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "run_sql",
        "description": (
            "execute a READ-ONLY SQL SELECT query against the app database. "
            "tables available: products, conversations, messages. "
            "only use existing columns from the provided schema."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "a complete sql SELECT statement. "
                        "must start with SELECT."
                    ),
                }
            },
            "required": ["query"],
        },
    },
}
