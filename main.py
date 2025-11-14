# main.py
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
import schemas
from database import Base, engine, SessionLocal

# create tables on startup (prototype degenerate migration strategy)
Base.metadata.create_all(bind=engine)


app = FastAPI(title="chat backend prototype")


# dev-only, totally open. tighten later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # or ["http://localhost:5500", ...]
    allow_credentials=False,
    allow_methods=["*"],          # allow POST, OPTIONS, etc
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/conversations", response_model=schemas.ConversationRead)
def create_conversation(
    _: schemas.ConversationCreate, db: Session = Depends(get_db)
):
    conv = models.Conversation()
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@app.get("/conversations", response_model=List[schemas.ConversationRead])
def list_conversations(db: Session = Depends(get_db)):
    return db.query(models.Conversation).order_by(models.Conversation.id.desc()).all()


@app.get(
    "/conversations/{conversation_id}",
    response_model=schemas.ConversationRead,
)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conv = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conv


@app.post(
    "/conversations/{conversation_id}/messages",
    response_model=schemas.MessageRead,
)
def add_message(
    conversation_id: int,
    payload: schemas.MessageCreate,
    db: Session = Depends(get_db),
):
    conv = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conversation_id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    msg = models.Message(
        conversation_id=conversation_id,
        role=payload.role,
        text=payload.text,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
