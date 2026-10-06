import asyncio
import json
import time
from contextlib import aclosing
from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4

from anyio import fail_after
from fastapi import HTTPException

from app.config import settings
from app.features.products.models import Product
from app.features.products.service import require
from app.features.retrieval.routes import RetrievalInput
from app.features.retrieval.service import retrieve


@dataclass
class ChatRun:
    product_id: str
    conversation_id: str
    revision_id: str
    release_id: str | None
    generation: int
    label: str
    id: str = field(default_factory=lambda: str(uuid4()))
    state: str = "running"
    sources: list = field(default_factory=list)
    ui: dict | None = None
    error: str | None = None
    started: float = field(default_factory=time.monotonic)


runs: dict[str, ChatRun] = {}
active_conversations: dict[str, tuple[str, float]] = {}
registry_lock = Lock()


def release_conversation(conversation_id, request_id):
    with registry_lock:
        reservation = active_conversations.get(conversation_id)
        if reservation and reservation[0] == request_id:
            active_conversations.pop(conversation_id, None)


def start_run(session, pid, conversation_id, messages, preview, revision_id, release_id, request_id=None):
    request_id = request_id or str(uuid4())
    now = time.monotonic()
    with registry_lock:
        for key, run in list(runs.items()):
            if now - run.started > 1800:
                del runs[key]
        for key, (_, started) in list(active_conversations.items()):
            if now - started > 180:
                del active_conversations[key]
        if conversation_id in active_conversations:
            raise HTTPException(409, "Wait for the current answer or clear the conversation")
        if request_id in runs or any(value[0] == request_id for value in active_conversations.values()):
            raise HTTPException(409, "Start a new answer with a new request identifier")
        if len(active_conversations) >= 3:
            raise HTTPException(503, "The assistant is busy. Try again shortly")
        active_conversations[conversation_id] = (request_id, now)
    try:
        product = require(session, Product, pid)
        retrieval = retrieve(
            session,
            pid,
            RetrievalInput(
                query=messages[-1].content,
                preview=preview,
                revision_id=revision_id,
                release_id=release_id,
                limit=5,
                mode="vector",
            ),
        )
        if not settings.openrouter_api_key or not settings.chat_gateway_token:
            raise HTTPException(503, "Configure the server OpenRouter connection before using chat")
        diagnostic = retrieval["diagnostics"]
        run = ChatRun(
            pid,
            conversation_id,
            diagnostic["revision_id"],
            diagnostic["release_id"],
            diagnostic["generation"],
            retrieval["label"],
            id=request_id,
        )
        add_sources(run, retrieval["results"])
        with registry_lock:
            if len(runs) >= 500:
                oldest = min(
                    (r for r in runs.values() if r.state != "running"), key=lambda r: r.started, default=None
                )
                if oldest:
                    runs.pop(oldest.id, None)
            runs[request_id] = run
        return run, {"name": product.name, "purpose": product.purpose}
    except Exception:
        release_conversation(conversation_id, request_id)
        raise


def get_run(pid, request_id):
    with registry_lock:
        run = runs.get(request_id)
        if run and time.monotonic() - run.started > 1800:
            runs.pop(request_id, None)
            run = None
        if not run or run.product_id != pid:
            raise HTTPException(404, "No answer for this request")
        return run


def add_sources(run, results):
    known = {s["chunk_id"] for s in run.sources}
    for hit in results:
        evidence = hit["evidence"]
        if evidence["chunk_id"] not in known and len(run.sources) < 20:
            run.sources.append({**evidence, "citation": f"S{len(run.sources) + 1}", "score": hit["score"]})
            known.add(evidence["chunk_id"])


def metadata(run):
    return {
        "id": run.id,
        "state": run.state,
        "revision_id": run.revision_id,
        "release_id": run.release_id,
        "generation": run.generation,
        "label": run.label,
        "sources": run.sources,
        "ui": run.ui,
        "error": run.error,
        "model": settings.chat_model,
    }


def validate_ui(node, run, depth=0, budget=None):
    budget = budget if budget is not None else [0]
    budget[0] += 1
    if depth > 6 or budget[0] > 60 or not isinstance(node, dict):
        raise ValueError("Keep the presentation small and structured")
    kind = node.get("$type")
    allowed = {
        "Col": {"children"},
        "Row": {"children"},
        "Card": {"title", "description", "children"},
        "Fact": {"label", "value"},
        "Table": {"columns", "rows", "sortable"},
        "Evidence": {"citations"},
    }
    if kind not in allowed or set(node) - allowed[kind] - {"$type"}:
        raise ValueError("Use only the available display components")
    if len(json.dumps(node)) > 20_000:
        raise ValueError("Keep the presentation concise")
    if "children" in node:
        if not isinstance(node["children"], list):
            raise ValueError("Children must be a list")
        for child in node["children"]:
            validate_ui(child, run, depth + 1, budget)
    if kind == "Evidence":
        known = {s["citation"] for s in run.sources}
        if not isinstance(node.get("citations"), list) or any(c not in known for c in node["citations"]):
            raise ValueError("Use citation identifiers from retrieved evidence")
    if kind == "Fact" and not {"label", "value"}.issubset(node):
        raise ValueError("Each fact needs a label and value")
    if kind == "Table":
        columns, rows = node.get("columns"), node.get("rows")
        if not isinstance(columns, list) or not 1 <= len(columns) <= 8:
            raise ValueError("Use at most eight columns")
        if any(
            not isinstance(c, dict) or set(c) != {"label"} or not isinstance(c["label"], str) for c in columns
        ):
            raise ValueError("Each column needs a text label")
        if (
            not isinstance(rows, list)
            or len(rows) > 30
            or any(
                not isinstance(row, list)
                or len(row) != len(columns)
                or any(not isinstance(value, (str, int, float, bool)) and value is not None for value in row)
                for row in rows
            )
        ):
            raise ValueError("Use a small table with scalar values")
    for key in ("title", "description", "label", "value"):
        if key in node and (not isinstance(node[key], (str, int, float)) or len(str(node[key])) > 2000):
            raise ValueError("Use concise display text")
    return node


async def agent_answer(run, product, messages):
    from app.features.chat.agent import events

    try:
        with fail_after(120):
            async with aclosing(events(run, product, messages)) as stream:
                async for text in stream:
                    yield text
        run.state = "complete"
    except (asyncio.CancelledError, GeneratorExit):
        run.state = "cancelled"
        raise
    except Exception:  # noqa: BLE001 - sanitize all SDK/provider failures at the HTTP stream boundary
        run.state = "failed"
        run.error = "The assistant could not finish this answer. Check the model connection and try again."
        yield "\n\n" + run.error

    finally:
        release_conversation(run.conversation_id, run.id)
