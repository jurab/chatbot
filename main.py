
# libraries
import os
import asyncio
import json

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from openai import OpenAI
from database import Base, engine, SessionLocal

# modules
import models
import schemas

# prompts
from prompts import SYSTEM_PROMPT
from tools import SQL_TOOL_SPEC


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_products():
    db = SessionLocal()
    try:
        # only seed once
        exists = db.query(models.Product).first()
        if exists:
            return

        demo_products = [
            models.Product(
                name="basic widget",
                price=9.99,
                description="a simple widget for everyday use.",
            ),
            models.Product(
                name="premium widget",
                price=29.99,
                description="fancier widget, allegedly worth it.",
            ),
            models.Product(
                name="mystery box",
                price=49.99,
                description="you probably shouldn't buy this.",
            ),
        ]
        db.add_all(demo_products)
        db.commit()
    finally:
        db.close()


seed_products()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_readonly_sql(db: Session, query: str):
    """execute a read-only sql query and return rows as dicts."""
    q = query.lstrip().lower()
    if not q.startswith("select"):
        raise ValueError("only SELECT queries are allowed in this environment")

    # extra paranoia if you want:
    # forbidden = ["pragma", "attach", "insert", "update", "delete", "drop", "alter"]
    # if any(tok in q for tok in forbidden):
    #     raise ValueError("query contains forbidden keywords")

    result = db.execute(text(query))
    rows = [dict(row._mapping) for row in result]
    return rows


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

    last_user = (
        db.query(models.Message)
        .filter_by(conversation_id=conversation_id, role="user")
        .order_by(models.Message.id.desc())
        .first()
    )
    if not last_user:
        raise HTTPException(status_code=400, detail="no user message to respond to")

    api_key = getattr(conv, "api_key", None) or os.getenv("OPENAI_API_KEY")

    async def event_generator():
        accumulated = ""

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

        client = OpenAI(api_key=api_key)

        # build chat history with a system prompt that mentions the tool
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
        ]
        messages.extend(
            {"role": m.role, "content": m.text}
            for m in conv.messages
            if m.role in ("user", "assistant")
        )

        tool_logs = []

        try:
            # simple tool loop: allow a few tool rounds max
            for _ in range(4):
                resp = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=messages,
                    tools=[SQL_TOOL_SPEC],
                    tool_choice="auto",
                )
                choice = resp.choices[0]
                msg = choice.message

                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    # record the assistant's tool call "reasoning" if present
                    if msg.content:
                        tool_logs.append(
                            {
                                "type": "assistant_tool_thought",
                                "content": msg.content,
                            }
                        )

                    for tc in tool_calls:
                        name = tc.function.name
                        args_str = tc.function.arguments or "{}"
                        try:
                            args = json.loads(args_str)
                        except json.JSONDecodeError:
                            args = {}
                        query = args.get("query", "")

                        result_payload: dict | list
                        try:
                            rows = run_readonly_sql(db, query)
                            result_payload = {"ok": True, "rows": rows}
                        except Exception as e:
                            result_payload = {"ok": False, "error": str(e)}

                        log_entry = {
                            "type": "tool_call",
                            "tool_name": name,
                            "query": query,
                            "result": result_payload,
                        }
                        tool_logs.append(log_entry)

                        # send tool log immediately to frontend
                        yield {
                            "event": "tool",
                            "data": json.dumps(log_entry),
                        }
                        await asyncio.sleep(0)

                        # feed tool result back into the model
                        messages.append(
                            {
                                "role": "assistant",
                                "content": msg.content or "",
                                "tool_calls": [
                                    {
                                        "id": tc.id,
                                        "type": "function",
                                        "function": {
                                            "name": name,
                                            "arguments": args_str,
                                        },
                                    }
                                ],
                            }
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "name": name,
                                "content": json.dumps(result_payload),
                            }
                        )

                    # continue loop after executing tools
                    continue

                # no tool calls: this is the final user-visible answer
                final_text = msg.content or ""
                # stream it char-by-char
                for ch in final_text:
                    accumulated += ch
                    yield {"event": "token", "data": ch}
                    await asyncio.sleep(0)
                break

        except Exception as e:
            err = f"[backend error: {e}]"
            accumulated += err
            yield {"event": "token", "data": err}

        # done event
        yield {"event": "done", "data": "[DONE]"}

        assistant_msg = models.Message(
            conversation_id=conversation_id,
            role="assistant",
            text=accumulated,
        )
        db.add(assistant_msg)
        db.commit()

    return EventSourceResponse(event_generator())
