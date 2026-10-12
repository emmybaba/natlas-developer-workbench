
import json
import os
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from gradio_client import Client
from pydantic import BaseModel, Field


app = FastAPI(
    title="N-ATLaS OpenAI-Compatible Gateway",
    version="0.2.0",
    description=(
        "An OpenAI-compatible API gateway forwarding requests "
        "to the existing N-ATLaS Gradio runtime."
    ),
)

# Swagger will display an Authorize button.
security = HTTPBearer()

GRADIO_URL = os.getenv("NATLAS_GRADIO_BASE_URL")
GATEWAY_KEY = os.getenv("NATLAS_GATEWAY_API_KEY")

_client = None


# --------------------------------------------------
# Request models
# --------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "N-ATLaS"
    messages: list[ChatMessage]
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=512, ge=1)
    stream: bool = False


# --------------------------------------------------
# Authentication
# --------------------------------------------------

def _authorize(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if not GATEWAY_KEY:
        raise HTTPException(
            status_code=503,
            detail="NATLAS_GATEWAY_API_KEY is not configured.",
        )

    if credentials.credentials != GATEWAY_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    return True


# --------------------------------------------------
# OpenAI-compatible model listing
# --------------------------------------------------

@app.get("/v1/models")
def list_models(
    authorized: bool = Depends(_authorize),
):
    return {
        "object": "list",
        "data": [
            {
                "id": "N-ATLaS",
                "object": "model",
                "created": 0,
                "owned_by": "N-ATLaS",
            }
        ],
    }


# --------------------------------------------------
# OpenAI-compatible chat completions
# --------------------------------------------------

@app.post("/v1/chat/completions")
def chat_completions(
    request: ChatRequest,
    authorized: bool = Depends(_authorize),
):
    global _client

    if not GRADIO_URL:
        raise HTTPException(
            status_code=503,
            detail="NATLAS_GRADIO_BASE_URL is not configured.",
        )

    if request.stream:
        raise HTTPException(
            status_code=400,
            detail=(
                "Streaming is not supported by this gateway yet. "
                "Set stream to false."
            ),
        )

    if not request.messages:
        raise HTTPException(
            status_code=400,
            detail="At least one message is required.",
        )

    # Validate message roles.
    allowed_roles = {"system", "user", "assistant"}

    for message in request.messages:
        if message.role not in allowed_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported message role: {message.role}",
            )

    if request.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="The final message must be a user message.",
        )

    # Separate system instructions from the conversation.
    system_parts = [
        message.content
        for message in request.messages
        if message.role == "system"
    ]

    conversation = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in request.messages
        if message.role in ("user", "assistant")
    ]

    # Forward system instructions through the Gradio interface.
    if system_parts:
        system_text = "\n\n".join(system_parts)

        for message in conversation:
            if message["role"] == "user":
                message["content"] = (
                    system_text + "\n\n" + message["content"]
                )
                break

    try:
        # Create the upstream client only when first needed.
        if _client is None:
            _client = Client(GRADIO_URL)

        started = time.time()

        result = _client.predict(
            messages_json=json.dumps(conversation),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            json_mode=False,
            api_name="/generate",
        )

        # Extract the generated text from the Gradio result.
        if isinstance(result, dict):
            content = str(result.get("text", result))
        elif isinstance(result, str):
            try:
                parsed = json.loads(result)

                if isinstance(parsed, dict) and "text" in parsed:
                    content = str(parsed["text"])
                else:
                    content = result

            except json.JSONDecodeError:
                content = result
        else:
            content = str(result)

        # Return an OpenAI-compatible chat completion.
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(started),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                # Token counts are not measured by this gateway.
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    except HTTPException:
        raise

    except Exception as exc:
        # Keep detailed upstream errors in the local server log.
        print(f"N-ATLaS upstream error: {type(exc).__name__}: {exc}")

        raise HTTPException(
            status_code=502,
            detail=(
                "The upstream N-ATLaS runtime request failed. "
                "Check the gateway terminal for details."
            ),
        ) from exc


# --------------------------------------------------
# Basic health check
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "running",
        "service": "N-ATLaS OpenAI-Compatible Gateway",
        "upstream_configured": bool(GRADIO_URL),
        "authentication_configured": bool(GATEWAY_KEY),
    }
