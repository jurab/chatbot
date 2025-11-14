# shell.py
import code
from database import SessionLocal
from models import Conversation, Message

db = SessionLocal()

banner = "sqlalchemy shell\nvars: db, Conversation, Message"

code.interact(banner=banner, local=locals())
