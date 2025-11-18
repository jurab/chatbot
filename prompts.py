DB_SCHEMA_DOC = """
database schema (sqlite):

table products:
  - id INTEGER PRIMARY KEY
  - name TEXT
  - price REAL
  - description TEXT

table conversations:
  - id INTEGER PRIMARY KEY
  - created_at DATETIME
  - api_key TEXT NULLABLE

table messages:
  - id INTEGER PRIMARY KEY
  - conversation_id INTEGER (fk -> conversations.id)
  - created_at DATETIME
  - role TEXT ('user' or 'assistant')
  - text TEXT
"""

SYSTEM_PROMPT = f'''
You are a helpful assistant for a tiny online shop.
You can query the internal sqlite database using the run_sql tool.
run_sql is READ-ONLY: only use SELECT queries.
You MUST NOT modify data.
Here is the database schema:

{DB_SCHEMA_DOC}
'''
