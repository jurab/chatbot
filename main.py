import os
import asyncio

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session
from openai import OpenAI

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
def create_conversation(
    _: schemas.ConversationCreate,
    db: Session = Depends(get_db),
):
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
    db.commit()

    return JSONResponse({"status": "ok"})


@app.get("/conversations/{conversation_id}/stream")
async def stream_assistant(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    conv = db.query(models.Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    # make sure we actually have something to answer
    last_user = (
        db.query(models.Message)
        .filter_by(conversation_id=conversation_id, role="user")
        .order_by(models.Message.id.desc())
        .first()
    )
    if not last_user:
        raise HTTPException(status_code=400, detail="no user message to respond to")

    # get api key from conversation or env
    api_key = getattr(conv, "api_key", None) or os.getenv("OPENAI_API_KEY")

    async def event_generator():
        accumulated = ""

        # if there's no key, just stream a boring error message
        if not api_key:
            msg = (
                "no api key configured. set it in the ui or via OPENAI_API_KEY env var."
            )
            for ch in msg:
                accumulated += ch
                yield {"event": "token", "data": ch}
                await asyncio.sleep(0)
            yield {"event": "done", "data": "[DONE]"}
            assistant_msg = models.Message(
                conversation_id=conversation_id,
                role="assistant",
                text=accumulated,
            )
            db.add(assistant_msg)
            db.commit()
            return

        # build chat history from db
        messages = [
            {"role": m.role, "content": m.text}
            for m in conv.messages
            if m.role in ("user", "assistant")
        ]

        # optional: prepend a system prompt later if you care
        client = OpenAI(api_key=api_key)

        try:
            stream = client.chat.completions.create(
                model="gpt-5-mini",
                messages=messages,
                stream=True,
            )

            for chunk in stream:
                choice = chunk.choices[0]
                delta = choice.delta
                token = getattr(delta, "content", None)

                if not token:
                    continue

                accumulated += token
                yield {"event": "token", "data": token}
                # yield control so we don't hard-block the loop
                await asyncio.sleep(0)

        except Exception as e:
            # surface backend error into the chat instead of just dying silently
            err = f"[backend error: {e}]"
            accumulated += err
            yield {"event": "token", "data": err}

        # final event
        yield {"event": "done", "data": "[DONE]"}

        # persist assistant message
        assistant_msg = models.Message(
            conversation_id=conversation_id,
            role="assistant",
            text=accumulated,
        )
        db.add(assistant_msg)
        db.commit()

    return EventSourceResponse(event_generator())
