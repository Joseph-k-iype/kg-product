"""Owned Anthropic Messages -> OpenAI Chat Completions translation via pinned LiteLLM."""

import json
import logging
import secrets
from contextvars import ContextVar
from inspect import isawaitable

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import settings

router = APIRouter(prefix="/internal/llm", include_in_schema=False)
private_provider_call = ContextVar("knowledge_private_provider_call", default=False)
SAFE_ERROR = "The model provider could not complete this request"


class PrivateProviderLogs(logging.Filter):
    def filter(self, record):
        return not private_provider_call.get()


def authorize(request):
    expected = settings.chat_gateway_token.get_secret_value() if settings.chat_gateway_token else ""
    supplied = request.headers.get("x-api-key") or request.headers.get("authorization", "").removeprefix(
        "Bearer "
    )
    if not expected or not secrets.compare_digest(supplied, expected):
        raise HTTPException(401, "Server gateway credential required")


async def close_stream(stream):
    close = getattr(stream, "aclose", None)
    if close:
        result = close()
        if isawaitable(result):
            await result


def sanitize_frame(frame):
    lines = frame.splitlines()
    payload = "\n".join(line[5:].strip() for line in lines if line.startswith("data:"))
    try:
        data = json.loads(payload)
    except ValueError:
        return ""
    if data.get("type") == "error" or any(line.strip() == "event: error" for line in lines):
        return (
            "event: error\ndata: "
            + json.dumps({"type": "error", "error": {"type": "api_error", "message": SAFE_ERROR}})
            + "\n\n"
        )
    return frame + "\n\n"


@router.post("/v1/messages")
async def messages(request: Request):
    authorize(request)
    if not settings.openrouter_api_key:
        raise HTTPException(503, "Configure the server OpenRouter connection")
    raw = await request.body()
    if len(raw) > 2_000_000:
        raise HTTPException(413, "Model request is too large")
    try:
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise TypeError("Expected an object")
        arguments = {
            key: body[key]
            for key in (
                "messages",
                "system",
                "tools",
                "tool_choice",
                "temperature",
                "top_p",
                "stop_sequences",
            )
            if key in body
        }
        maximum = max(1, min(int(body.get("max_tokens", 1200)), settings.chat_max_output_tokens))
    except (ValueError, TypeError):
        raise HTTPException(422, "Invalid model request")
    import litellm
    from litellm._logging import verbose_logger, verbose_proxy_logger, verbose_router_logger
    from litellm.llms.anthropic.experimental_pass_through.adapters.transformation import AnthropicAdapter

    for logger in (verbose_logger, verbose_proxy_logger, verbose_router_logger):
        if not any(isinstance(f, PrivateProviderLogs) for f in logger.filters):
            logger.addFilter(PrivateProviderLogs())
    adapter = AnthropicAdapter()
    streaming = bool(body.get("stream"))
    private_provider_call.set(True)
    try:
        request_body, names = adapter.translate_completion_input_params_with_tool_mapping(
            {
                **arguments,
                "model": "openrouter/" + settings.chat_model,
                "max_tokens": maximum,
                "stream": streaming,
            },
            custom_llm_provider="openrouter",
        )
        if request_body is None:
            raise ValueError("Invalid message format")
        upstream = await litellm.acompletion(
            **request_body,
            api_key=settings.openrouter_api_key.get_secret_value(),
            api_base="https://openrouter.ai/api/v1",
            timeout=40,
            num_retries=0,
            drop_params=True,
        )
    except Exception:  # noqa: BLE001 - sanitize all provider/request failures
        raise HTTPException(502, SAFE_ERROR)
    finally:
        private_provider_call.set(False)
    if not streaming:
        return adapter.translate_completion_output_params(upstream, tool_name_mapping=names)

    async def provider_chunks():
        try:
            async for chunk in upstream:
                yield chunk
        except Exception:  # noqa: BLE001 - keep raw exceptions out of adapter events/logs
            raise RuntimeError(SAFE_ERROR) from None

    guarded = provider_chunks()
    translated = adapter.translate_completion_output_params_streaming(
        guarded,
        model=settings.chat_model,
        tool_name_mapping=names,
        is_async=True,
    )

    async def events():
        private_provider_call.set(True)
        buffer = ""
        try:
            async for event in translated:
                buffer += event.decode("utf-8") if isinstance(event, bytes) else event
                while "\n\n" in buffer:
                    frame, buffer = buffer.split("\n\n", 1)
                    yield sanitize_frame(frame)
            if buffer.strip():
                yield sanitize_frame(buffer)
        finally:
            try:
                await close_stream(translated)
                await close_stream(guarded)
            finally:
                await close_stream(upstream)
                private_provider_call.set(False)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/v1/messages/count_tokens")
async def count_tokens(request: Request):
    authorize(request)
    body = await request.body()
    return {"input_tokens": max(1, (len(body) + 2) // 3)}
