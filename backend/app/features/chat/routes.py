from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.features.chat import service
from app.features.products.models import Product
from app.features.products.service import require

router = APIRouter(prefix="/api")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class ChatInput(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    page: dict | None = None

    @model_validator(mode="after")
    def bounded(self):
        if self.messages[-1].role != "user" or not self.messages[-1].content.strip():
            raise ValueError("End the conversation with a question")
        if len(self.messages[-1].content) > 2000 or sum(len(m.content) for m in self.messages) > 24000:
            raise ValueError("Keep the question and conversation shorter")
        return self


@router.get("/chat/status")
def status():
    return {
        "configured": bool(settings.openrouter_api_key and settings.chat_gateway_token),
        "model": settings.chat_model,
        "agent": "Claude Agent SDK",
        "gateway": "LiteLLM",
    }


@router.post("/products/{id}/chat")
def chat(
    id: str,
    input: ChatInput,
    session: Annotated[Session, Depends(get_session, scope="function")],
    preview: bool = False,
    revision_id: str | None = None,
    release_id: str | None = None,
    conversation_id: UUID | None = None,
    request_id: UUID | None = None,
):
    run, product = service.start_run(
        session,
        id,
        str(conversation_id or uuid4()),
        input.messages,
        preview,
        revision_id,
        release_id,
        str(request_id or uuid4()),
    )
    return StreamingResponse(
        service.agent_answer(run, product, input.messages),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no", "X-Chat-Run": run.id},
    )


@router.get("/products/{id}/chat/runs/{request_id}")
def run(id: str, request_id: UUID, session: Annotated[Session, Depends(get_session, scope="function")]):
    require(session, Product, id)
    return service.metadata(service.get_run(id, str(request_id)))
