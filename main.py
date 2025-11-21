# libraries
import os
import asyncio
import json
import traceback

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

# seed_mediaplan.py
import csv
from datetime import datetime
from models import MediaPlanRow

# prompts
# SYSTEM_PROMPT: main agent behavior, including how to use sql tools
# SAFETY_SYSTEM_PROMPT: separate prompt just for the security pre-check
from prompts import SAFETY_SYSTEM_PROMPT, SYSTEM_PROMPT
from tools import SQL_TOOL_SPEC


# create db schema if it doesn't exist yet
Base.metadata.create_all(bind=engine)

# fastapi app instance
app = FastAPI()

# super permissive CORS so the demo frontend can call this from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _strip_or_none(x: str | None) -> str | None:
    if x is None:
        return None
    x = x.strip()
    return x or None


def parse_date(x: str | None, field: str, rownum: int):
    s = _strip_or_none(x)
    if s is None:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        raise ValueError(f"invalid date in column '{field}' row {rownum}: {s!r}")


def parse_float(x: str | None, field: str, rownum: int):
    s = _strip_or_none(x)
    if s is None:
        return None
    try:
        return float(s)
    except Exception:
        raise ValueError(f"invalid float in column '{field}' row {rownum}: {s!r}")


def parse_int(x: str | None, field: str, rownum: int):
    s = _strip_or_none(x)
    if s is None:
        return None
    try:
        # allow "3.0" etc
        return int(float(s))
    except Exception:
        raise ValueError(f"invalid int in column '{field}' row {rownum}: {s!r}")


def seed_mediaplan_from_csv(path: str):
    db = SessionLocal()
    try:
        # only seed once
        exists = db.query(MediaPlanRow).first()
        if exists:
            return

        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            rows = []
            for idx, row in enumerate(reader, start=2):  # header is row 1
                r = MediaPlanRow(
                    source=row["source"],
                    type=row["type"],
                    department=row["department"],
                    bu_cost_center=row["bu_cost_center"],
                    billed_cost_center=row["billed_cost_center"],
                    cost_center=row["cost_center"],
                    business_unit=row["business_unit"],
                    business_internal=row["business_internal"],
                    revenue_type=row["revenue_type"],
                    cc_costs_type=row["cc_costs_type"],
                    bu_costs_type=row["bu_costs_type"],
                    client=row["client"],
                    client_status=row["client_status"],
                    pm=row["pm"],
                    sm=row["sm"],
                    project_id=row["project_id"],
                    project=row["project"],
                    project_status=row["project_status"],
                    category=row["category"],
                    detail=row["detail"],
                    media_type=row["media_type"],
                    paid_by=row["paid_by"],

                    month=parse_int(row["month"], "month", idx),
                    year=parse_int(row["year"], "year", idx),

                    duzp=parse_date(row["duzp"], "duzp", idx),
                    cf_date=parse_date(row["cf_date"], "cf_date", idx),
                    dph_date=parse_date(row["dph_date"], "dph_date", idx),

                    id_mediaplan=parse_int(row["id_mediaplan"], "id_mediaplan", idx),
                    mediaplan=row["mediaplan"],
                    invoice_number=row["invoice_number"],
                    invoice_issue_date=parse_date(row["invoice_issue_date"], "invoice_issue_date", idx),
                    invoice_due_date=parse_date(row["invoice_due_date"], "invoice_due_date", idx),
                    invoice_payment_date=parse_date(row["invoice_payment_date"], "invoice_payment_date", idx),

                    forecast_level=parse_int(row["forecast_level"], "forecast_level", idx),
                    main_status=row["main_status"],
                    finance_status=row["finance_status"],
                    cf_status=row["cf_status"],
                    probability=parse_float(row["probability"], "probability", idx),
                    hours=parse_float(row["hours"], "hours", idx),

                    firma=row["firma"],
                    industry=row["industry"],
                    cost_category=row["cost_category"],
                    fc_source=row["fc_source"],
                    fc_source_prepayments=row["fc_source_prepayments"],
                    client_logo=row["client_logo"],
                    pm_email=row["pm_email"],
                    pm_picture=row["pm_picture"],

                    price_fc_revenues=parse_float(row["price_fc_revenues"], "price_fc_revenues", idx),
                    price_fc_revenues_prepayments=parse_float(row["price_fc_revenues_prepayments"], "price_fc_revenues_prepayments", idx),
                    price_fc_costs=parse_float(row["price_fc_costs"], "price_fc_costs", idx),
                    price_fc_costs_prepayments=parse_float(row["price_fc_costs_prepayments"], "price_fc_costs_prepayments", idx),

                    price_bp_revenues=parse_float(row["price_bp_revenues"], "price_bp_revenues", idx),
                    price_bp_revenues_prepayments=parse_float(row["price_bp_revenues_prepayments"], "price_bp_revenues_prepayments", idx),
                    price_bp_costs=parse_float(row["price_bp_costs"], "price_bp_costs", idx),
                    price_bp_costs_prepayments=parse_float(row["price_bp_costs_prepayments"], "price_bp_costs_prepayments", idx),

                    price_bp_revised_revenues=parse_float(row["price_bp_revised_revenues"], "price_bp_revised_revenues", idx),
                    price_bp_revised_revenues_prepayments=parse_float(row["price_bp_revised_revenues_prepayments"], "price_bp_revised_revenues_prepayments", idx),
                    price_bp_revised_costs=parse_float(row["price_bp_revised_costs"], "price_bp_revised_costs", idx),
                    price_bp_revised_costs_prepayments=parse_float(row["price_bp_revised_costs_prepayments"], "price_bp_revised_costs_prepayments", idx),

                    price_real_revenues=parse_float(row["price_real_revenues"], "price_real_revenues", idx),
                    price_real_revenues_prepayments=parse_float(row["price_real_revenues_prepayments"], "price_real_revenues_prepayments", idx),
                    price_real_revenues_findb=parse_float(row["price_real_revenues_findb"], "price_real_revenues_findb", idx),
                    price_real_costs=parse_float(row["price_real_costs"], "price_real_costs", idx),

                    forecast_fc_revenues=parse_float(row["forecast_fc_revenues"], "forecast_fc_revenues", idx),
                    forecast_fc_revenues_prepayments=parse_float(row["forecast_fc_revenues_prepayments"], "forecast_fc_revenues_prepayments", idx),
                    forecast_fc_costs=parse_float(row["forecast_fc_costs"], "forecast_fc_costs", idx),
                    forecast_fc_costs_prepayments=parse_float(row["forecast_fc_costs_prepayments"], "forecast_fc_costs_prepayments", idx),
                    forecast_fc_revenue_cm=parse_float(row["forecast_fc_revenue_cm"], "forecast_fc_revenue_cm", idx),
                    forecast_fc_costs_cm=parse_float(row["forecast_fc_costs_cm"], "forecast_fc_costs_cm", idx),

                    forecast_fc_real_up_to_date_revenues=parse_float(row["forecast_fc_real_up_to_date_revenues"], "forecast_fc_real_up_to_date_revenues", idx),
                    forecast_fc_real_up_to_date_revenues_prepayments=parse_float(row["forecast_fc_real_up_to_date_revenues_prepayments"], "forecast_fc_real_up_to_date_revenues_prepayments", idx),
                    price_fc_real_up_to_date_revenues_prepayments=parse_float(row["price_fc_real_up_to_date_revenues_prepayments"], "price_fc_real_up_to_date_revenues_prepayments", idx),
                    forecast_fc_real_up_to_date_costs=parse_float(row["forecast_fc_real_up_to_date_costs"], "forecast_fc_real_up_to_date_costs", idx),
                    forecast_fc_real_up_to_date_costs_prepayments=parse_float(row["forecast_fc_real_up_to_date_costs_prepayments"], "forecast_fc_real_up_to_date_costs_prepayments", idx),
                    price_fc_real_up_to_date_costs_prepayments=parse_float(row["price_fc_real_up_to_date_costs_prepayments"], "price_fc_real_up_to_date_costs_prepayments", idx),
                )
                rows.append(r)

            # all parsed ok => bulk insert
            db.add_all(rows)
            db.commit()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# seed once when the module is imported
seed_mediaplan_from_csv("mediaplan.csv")


def get_db():
    """
    standard fastapi dependency that yields a db session
    and makes sure it's closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_readonly_sql(db: Session, query: str):
    """
    execute a read-only sql query and return rows as dicts.

    this is intentionally a bit naive, to keep the workshop interesting:
    - enforces that the query starts with SELECT
    - does not deeply validate the rest of the statement
    - uses sqlalchemy.text for raw sql
    """
    try:
        q = query.lstrip().lower()
        if not q.startswith("select"):
            # we only allow SELECT to avoid obvious write operations
            raise ValueError("only SELECT queries are allowed in this environment")

        # extra paranoia if you want to lock things down further:
        # forbidden = ["pragma", "attach", "insert", "update", "delete", "drop", "alter"]
        # if any(tok in q for tok in forbidden):
        #     raise ValueError("query contains forbidden keywords")

        result = db.execute(text(query))
        # convert each row to a plain dict so it's easy to json-serialize
        rows = [dict(row._mapping) for row in result]

    except Exception as e:
        print(traceback.format_exc())
        raise e

    return rows


def run_safety_check(client: OpenAI, user_text: str) -> dict:
    """
    run a dedicated safety / security check on the latest user message.

    flow:
    - call openai with SAFETY_SYSTEM_PROMPT + the user text
    - expect JSON (object) back describing:
        { "safe": bool, "reason": str, "category": str }
    - if anything fails, log traceback and return a "safe: true, error" object
      (fail-open, but indicate that the safety layer had issues)

    this function is *defined* here but wired into the stream handler below
    (currently commented out for demo purposes).
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-5-mini",  # or any model you want to use for safety
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SAFETY_SYSTEM_PROMPT},
                {"role": "user", "content": user_text or ""},
            ],
        )

        # the model is supposed to respond with a json object as a string
        raw = resp.choices[0].message.content or "{}"

        # parse json result
        data = json.loads(raw)
        if not isinstance(data, dict):
            # we insisted on a single json object; bail if not
            raise ValueError("safety response not a json object")

        # ensure required keys exist, even if the model omitted them
        data.setdefault("safe", True)
        data.setdefault("reason", "safety model returned incomplete json")
        data.setdefault("category", "unknown")

        return data

    except Exception as e:
        # for debugging: print full traceback to server logs
        print(traceback.format_exc())
        # fail-open, but explicitly mark this as an error in the reason/category
        return {
            "safe": True,
            "reason": f"safety_check_error: {e}",
            "category": "error",
        }


@app.post("/conversations", response_model=schemas.ConversationRead)
def create_conversation(
    _: schemas.ConversationCreate,
    db: Session = Depends(get_db),
):
    """
    create a new conversation row and return it.

    the request body is currently unused except for validation via ConversationCreate.
    """
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
    """
    append a user message to an existing conversation.

    behavior:
    - look up conversation by id
    - if payload includes a "key", store it on the conversation as api_key
      (this is intentionally insecure in a real-world sense, for demo purposes)
    - store the user message text in the Message table
    """
    conv = db.query(models.Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    # stash api key on the conversation for later use by the streaming endpoint
    if getattr(payload, "key", None):
        conv.api_key = payload.key

    # persist the user message
    user_msg = models.Message(
        conversation_id=conversation_id,
        role="user",
        text=payload.text,
    )
    db.add(user_msg)
    db.commit()

    # minimal response; the frontend doesn't need the newly created message here
    return JSONResponse({"status": "ok"})


@app.get("/conversations/{conversation_id}/stream")
async def stream_assistant(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """
    server-sent-events endpoint that streams the assistant reply.

    behavior:
    - finds the conversation and latest user message
    - uses either:
        - the per-conversation api_key (if user provided one), or
        - the OPENAI_API_KEY from the environment
    - (optionally) runs a safety check on the latest user message
    - runs the main tool-using agent loop with sql access
    - streams out:
        - "token" events for assistant text, 1 char at a time
        - "tool" events when tools are called (including query + result)
        - "done" event at the end

    note: the safety section is temporarily commented out so you can demo
    the unsafe behavior first, then enable the filter live.
    """
    conv = db.query(models.Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="conversation not found")

    # grab the latest user message in this conversation
    last_user = (
        db.query(models.Message)
        .filter_by(conversation_id=conversation_id, role="user")
        .order_by(models.Message.id.desc())
        .first()
    )
    if not last_user:
        raise HTTPException(status_code=400, detail="no user message to respond to")

    # choose api key: user-scoped key in db, or global env key
    api_key = getattr(conv, "api_key", None) or os.getenv("OPENAI_API_KEY")

    async def event_generator():
        """
        async generator that yields SSE events.

        note: fastapi + sse-starlette expects this pattern:
        - yield dicts with "event" and "data"
        - wrap with EventSourceResponse at the end of the route
        """
        accumulated = ""  # collect everything we stream, to persist as assistant message

        if not api_key:
            # if there's no key at all, we stream a friendly error message
            msg = (
                "no api key configured. set it in the ui or via OPENAI_API_KEY env var."
            )
            for ch in msg:
                accumulated += ch
                # send one character per event so the frontend shows incremental typing
                yield {"event": "token", "data": ch}
                await asyncio.sleep(0)
            # signal completion
            yield {"event": "done", "data": "[DONE]"}
            # store this "assistant" response in the db
            assistant_msg = models.Message(
                conversation_id=conversation_id,
                role="assistant",
                text=accumulated,
            )
            db.add(assistant_msg)
            db.commit()
            return

        # create openai client with the chosen key
        client = OpenAI(api_key=api_key)

        # ------------------------------------------------------------------
        # OPTIONAL SAFETY LAYER (currently disabled for demo purposes)
        #
        # if you want to enable the llm-based firewall, uncomment this block.
        # workflow:
        #   1) run_safety_check() on the last user message
        #   2) emit a "safety" event so the frontend can show/log the verdict
        #   3) if safe == false, stream a blocking message and bail *before*
        #      invoking the main model or any tools.
        # ------------------------------------------------------------------

        safety = run_safety_check(client, last_user.text or "")

        # stream safety decision as a separate event for the frontend to inspect/log
        try:
            yield {
                "event": "safety",
                "data": json.dumps(safety),
            }
            await asyncio.sleep(0)
        except Exception:
            # if sending the safety event via SSE fails, ignore it;
            # the main flow still runs (fail-open on telemetry, not on functionality)
            pass

        if not safety.get("safe", True):
            # if the safety filter flags this as unsafe, we *do not* call tools or main model
            msg = (
                "this request was blocked by the security filter.\n\n"
                f"reason: {safety.get('reason', '')}\n"
                f"category: {safety.get('category', 'unknown')}"
            )
            for ch in msg:
                accumulated += ch
                yield {"event": "token", "data": ch}
                await asyncio.sleep(0)

            # signal completion
            yield {"event": "done", "data": "[DONE]"}

            # persist the blocking message as an assistant response
            assistant_msg = models.Message(
                conversation_id=conversation_id,
                role="assistant",
                text=accumulated,
            )
            db.add(assistant_msg)
            db.commit()
            return

        # ------------------------------------------------------------------
        # MAIN TOOL-USING ASSISTANT FLOW
        # ------------------------------------------------------------------

        # build chat history with system prompt + all prior user/assistant turns
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

        # place to stash tool logs for debugging / observability (also streamed to frontend)
        tool_logs = []

        try:
            # allow a limited number of tool iterations (e.g. 4) to avoid infinite loops
            for _ in range(4):
                resp = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=messages,
                    tools=[SQL_TOOL_SPEC],
                    tool_choice="auto",  # model decides if/when to call the tool
                )
                choice = resp.choices[0]
                msg = choice.message

                # tool_calls is where the model specifies sql queries via the tool schema
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    # model might also include natural language "reasoning" in msg.content
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
                            # if arguments are garbage, we treat as empty
                            args = {}
                        query = args.get("query", "")

                        result_payload: dict | list
                        try:
                            # run the sql in read-only mode and capture rows
                            rows = run_readonly_sql(db, query)
                            result_payload = {"ok": True, "rows": rows}
                        except Exception as e:
                            # if sql fails, capture the error so the model can react
                            result_payload = {"ok": False, "error": str(e)}

                        log_entry = {
                            "type": "tool_call",
                            "tool_name": name,
                            "query": query,
                            "result": result_payload,
                        }
                        tool_logs.append(log_entry)

                        # send tool log immediately to frontend so users can see
                        # exactly what sql got executed and what came back
                        yield {
                            "event": "tool",
                            "data": json.dumps(log_entry),
                        }
                        await asyncio.sleep(0)

                        # feed the tool call + result back into the conversation
                        # so the model can generate a final answer that uses it
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

                    # after handling tool calls, go back to the top of the loop
                    # and let the model see the tool responses
                    continue

                # if we get here, there were no tool calls: msg.content is the final answer
                final_text = msg.content or ""
                # stream the final answer character-by-character
                for ch in final_text:
                    accumulated += ch
                    yield {"event": "token", "data": ch}
                    await asyncio.sleep(0)
                break

        except Exception as e:
            # any unexpected backend error gets streamed as part of the assistant text
            err = f"[backend error: {e}]"
            accumulated += err
            yield {"event": "token", "data": err}

        # signal that streaming is done
        yield {"event": "done", "data": "[DONE]"}

        # persist the assistant message (whatever accumulated) to the db
        assistant_msg = models.Message(
            conversation_id=conversation_id,
            role="assistant",
            text=accumulated,
        )
        db.add(assistant_msg)
        db.commit()

    # wrap the async generator in an SSE response
    return EventSourceResponse(event_generator())
