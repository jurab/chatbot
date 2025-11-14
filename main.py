from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session
import asyncio

import models
import schemas
from database import Base, engine, SessionLocal

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/conversations", response_model=schemas.ConversationRead)
def create_conversation(_: schemas.ConversationCreate, db: Session = Depends(get_db)):
    conv = models.Conversation()
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@app.post("/conversations/{conversation_id}/messages")
def add_user_message(
    conversation_id: int,
    payload: schemas.MessageCreate,
    db: Session = Depends(get_db),
):
    conv = db.query(models.Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    # stash api key on the conversation for later use
    if getattr(payload, "key", None):
        conv.api_key = payload.key

    # store the user message
    user_msg = models.Message(
        conversation_id=conversation_id,
        role="user",
        text=payload.text,
    )
    db.add(user_msg)
    # conv is already in the session, just commit
    db.commit()

    return JSONResponse({"status": "ok"})


@app.get("/conversations/{conversation_id}/stream")
async def stream_assistant(conversation_id: int, db: Session = Depends(get_db)):

    conv = db.query(models.Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    # get last user message (just for mock)
    last_user = (
        db.query(models.Message)
        .filter_by(conversation_id=conversation_id, role="user")
        .order_by(models.Message.id.desc())
        .first()
    )
    if not last_user:
        raise HTTPException(status_code=400, detail="no user message to respond to")

    api_key = getattr(conv, "api_key", None) or "<no key set>"

    reply = f"user message received, text: {last_user.text}, key: {api_key}"

    async def event_generator():
        accumulated = ""

        for char in reply:
            accumulated += char
            yield {"event": "token", "data": char}
            await asyncio.sleep(0.02)

        # final event
        yield {"event": "done", "data": "[DONE]"}

        # write complete assistant message to db
        assistant_msg = models.Message(
            conversation_id=conversation_id,
            role="assistant",
            text=accumulated,
        )
        db.add(assistant_msg)
        db.commit()

    return EventSourceResponse(event_generator())
