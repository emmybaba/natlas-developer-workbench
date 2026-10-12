import hmac
import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from evaluation.runner import load_cases, run_case
from sdk.natlas_sdk import AppError, NAtlas, OutputError, PromptApp, load_apps
from sdk.natlas_sdk.apps import NAME as APP_NAME


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATASET_DIR = Path(
    os.getenv("NATLAS_DATASET_DIR")
    or BASE_DIR.parent / "datasets" / "prompts"
)

APPS_DIR = Path(
    os.getenv("NATLAS_APPS_DIR")
    or BASE_DIR.parent / "apps"
)
MAX_INPUT_CHARS = 50000

INFERENCE_FAILED = (
    "Inference failed. Check the runtime configuration "
    "and inference service availability."
)

# id -> (label, environment variables that must be set to use it)
RUNTIMES = {
    "gradio": ("Gradio Space (community)", ["NATLAS_GRADIO_BASE_URL"]),
    "openai": (
        "OpenAI-compatible endpoint",
        ["NATLAS_BASE_URL", "NATLAS_API_KEY"],
    ),
    "llama_cpp": ("Local GGUF (llama.cpp)", ["NATLAS_MODEL_PATH"]),
    "mock": ("Mock (offline, no model)", []),
}


app = FastAPI(
    title="N-ATLaS Developer Workbench",
    description="Backend for the N-ATLaS Developer Workbench",
    version="0.3.0",
)


class GenerationOptions(BaseModel):
    runtime: Optional[str] = None
    system: Optional[str] = Field(default=None, max_length=8000)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4096)


class GenerateRequest(GenerationOptions):
    prompt: str


class GenerateResponse(BaseModel):
    response: str
    runtime: str
    latency_ms: int


class CompareRequest(GenerationOptions):
    prompt: str
    runtimes: List[str] = Field(min_length=2, max_length=4)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)


class ChatRequest(GenerationOptions):
    messages: List[ChatMessage] = Field(min_length=1, max_length=60)


class AppSpecRequest(BaseModel):
    spec: Dict[str, Any]


class AppTestRequest(GenerationOptions):
    spec: Dict[str, Any]
    inputs: Dict[str, Any] = {}


class AppRunRequest(GenerationOptions):
    inputs: Dict[str, Any] = {}


class EvaluateCaseRequest(GenerationOptions):
    dataset: Optional[str] = None
    case_id: Optional[str] = None
    case: Optional[dict] = None


# One SDK client per runtime, so a Gradio connection is reused between
# requests instead of being re-established for every prompt.
_clients = {}


def default_runtime() -> str:
    return os.getenv("NATLAS_RUNTIME", "gradio").lower()


def resolve_runtime(runtime: Optional[str]) -> str:
    runtime = (runtime or default_runtime()).lower()

    if runtime not in RUNTIMES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown runtime: {runtime}",
        )

    return runtime


def get_client(runtime: Optional[str] = None):
    key = runtime or "default"
    client = _clients.get(key)

    if client is None:
        client = NAtlas(runtime_type=runtime) if runtime else NAtlas()
        _clients[key] = client

    return client


def clear_clients() -> None:
    _clients.clear()


def run_generation(runtime, prompt, system=None, temperature=None, max_tokens=None):
    """Generate with timing. ``runtime`` may be None for the default."""

    start = time.perf_counter()
    text = get_client(runtime).generate(
        prompt,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return {
        "response": text,
        "runtime": runtime or default_runtime(),
        "latency_ms": round((time.perf_counter() - start) * 1000),
    }


def run_chat(runtime, messages, system=None, temperature=None, max_tokens=None):
    """Chat with timing. ``messages`` is a list of role/content dicts."""

    start = time.perf_counter()
    text = get_client(runtime).chat(
        messages,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return {
        "response": text,
        "runtime": runtime or default_runtime(),
        "latency_ms": round((time.perf_counter() - start) * 1000),
    }


def describe_error(error: Exception) -> str:
    # Configuration problems come from this project and are safe to show.
    # Anything else is reduced to its type so endpoint details do not leak.
    if isinstance(error, (ValueError, FileNotFoundError, ImportError)):
        return f"{type(error).__name__}: {error}"

    return type(error).__name__


def require_prompt(prompt: str) -> str:
    prompt = prompt.strip()

    if not prompt:
        raise HTTPException(
            status_code=422,
            detail="Prompt must not be empty.",
        )

    return prompt


def dataset_files() -> dict:
    if not DATASET_DIR.is_dir():
        return {}

    return {path.stem: path for path in sorted(DATASET_DIR.glob("*.jsonl"))}


def load_dataset(name: str) -> list:
    path = dataset_files().get(name)

    if path is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        return load_cases(path)
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from None


@app.get("/")
def playground():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "N-ATLaS Developer Workbench",
    }


@app.get("/api/runtimes")
def runtimes():
    """List runtimes and whether their configuration is present.

    ``configured`` only reports that the environment variables are set. It does
    not establish that the inference service is reachable.
    """

    default = default_runtime()
    items = []

    for runtime_id, (label, env) in RUNTIMES.items():
        missing = [name for name in env if not os.getenv(name)]

        items.append(
            {
                "id": runtime_id,
                "label": label,
                "configured": not missing,
                "missing_env": missing,
                "default": runtime_id == default,
            }
        )

    return {"runtimes": items}


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    prompt = require_prompt(request.prompt)
    runtime = resolve_runtime(request.runtime) if request.runtime else None

    try:
        return GenerateResponse(
            **run_generation(
                runtime,
                prompt,
                system=request.system,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        )

    except Exception:
        logger.exception("N-ATLaS inference request failed.")

        raise HTTPException(
            status_code=502,
            detail=INFERENCE_FAILED,
        ) from None


@app.post("/api/chat", response_model=GenerateResponse)
def chat(request: ChatRequest):
    """Continue a conversation. The client sends the whole history each time."""

    messages = [m.model_dump() for m in request.messages]

    if messages[-1]["role"] != "user" or not messages[-1]["content"].strip():
        raise HTTPException(
            status_code=422,
            detail="The last message must be a non-empty user message.",
        )

    runtime = resolve_runtime(request.runtime) if request.runtime else None

    try:
        return GenerateResponse(
            **run_chat(
                runtime,
                messages,
                system=request.system,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        )

    except Exception:
        logger.exception("N-ATLaS chat request failed.")

        raise HTTPException(
            status_code=502,
            detail=INFERENCE_FAILED,
        ) from None


@app.post("/api/compare")
def compare(request: CompareRequest):
    """Send one prompt to several runtimes and return each outcome."""

    prompt = require_prompt(request.prompt)
    runtime_ids = [resolve_runtime(item) for item in request.runtimes]

    if len(set(runtime_ids)) != len(runtime_ids):
        raise HTTPException(
            status_code=422,
            detail="Choose different runtimes to compare.",
        )

    def attempt(runtime_id):
        try:
            return {
                "ok": True,
                **run_generation(
                    runtime_id,
                    prompt,
                    system=request.system,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                ),
            }
        except Exception as error:
            logger.exception("Comparison request failed for %s.", runtime_id)
            return {
                "ok": False,
                "runtime": runtime_id,
                "error": describe_error(error),
            }

    with ThreadPoolExecutor(max_workers=len(runtime_ids)) as pool:
        results = list(pool.map(attempt, runtime_ids))

    return {"results": results}


@app.get("/api/datasets")
def datasets():
    items = []

    for name in dataset_files():
        try:
            count = len(load_dataset(name))
        except HTTPException:
            count = None

        items.append({"name": name, "cases": count})

    return {"datasets": items}


@app.get("/api/datasets/{name}")
def dataset(name: str):
    return {"name": name, "cases": load_dataset(name)}


@app.post("/api/evaluate/case")
def evaluate_case(request: EvaluateCaseRequest):
    """Run one case (from a dataset, or inline) and return its checked result.

    The browser calls this once per case so it can show progress and stop
    early.
    """

    runtime = resolve_runtime(request.runtime) if request.runtime else None

    if request.dataset:
        cases = {case["id"]: case for case in load_dataset(request.dataset)}
        case = cases.get(request.case_id or "")

        if case is None:
            raise HTTPException(status_code=404, detail="Case not found.")
    elif request.case is not None:
        case = request.case
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide a dataset and case_id, or an inline case.",
        )

    def generate_text(prompt, **options):
        return run_generation(runtime, prompt, **options)["response"]

    try:
        return run_case(
            case,
            generate_text,
            system=request.system,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


# ---------------------------------------------------------------- prompt apps
#
# Apps are JSON files in APPS_DIR (see sdk/natlas_sdk/apps.py). They are
# validated before anything is written, and names are restricted to
# lowercase letters, digits and hyphens so they cannot point outside APPS_DIR.


def build_app(spec) -> PromptApp:
    try:
        return PromptApp(spec)
    except AppError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


def app_file(name: str) -> Path:
    if not APP_NAME.match(name):
        raise HTTPException(status_code=404, detail="App not found.")

    return APPS_DIR / f"{name}.json"


def load_app(name: str) -> PromptApp:
    path = app_file(name)

    if not path.is_file():
        raise HTTPException(status_code=404, detail="App not found.")

    try:
        return PromptApp.from_file(path)
    except AppError as error:
        raise HTTPException(status_code=500, detail=str(error)) from None


def check_inputs(inputs: dict) -> None:
    for key, value in inputs.items():
        if len(str(value)) > MAX_INPUT_CHARS:
            raise HTTPException(
                status_code=422,
                detail=f"Input '{key}' is longer than {MAX_INPUT_CHARS} characters.",
            )


def execute_app(prompt_app, inputs, runtime, temperature=None, max_tokens=None):
    """Run an app and describe the outcome without raising.

    Returns ``{"ok": True, "output", "raw", ...}`` or
    ``{"ok": False, "kind": "input" | "output" | "inference", "error", ...}``.
    """

    check_inputs(inputs)
    start = time.perf_counter()

    try:
        result = prompt_app.run(
            get_client(runtime),
            inputs,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except OutputError as error:
        return {"ok": False, "kind": "output", "error": str(error), "raw": error.raw}
    except AppError as error:
        return {"ok": False, "kind": "input", "error": str(error)}
    except Exception:
        logger.exception("N-ATLaS app run failed.")
        return {"ok": False, "kind": "inference", "error": INFERENCE_FAILED}

    return {
        "ok": True,
        "output": result.output,
        "raw": result.raw,
        "attempts": result.attempts,
        "system": result.system,
        "prompt": result.prompt,
        "runtime": runtime or default_runtime(),
        "latency_ms": round((time.perf_counter() - start) * 1000),
    }


def app_summary(prompt_app: PromptApp) -> dict:
    return {
        "name": prompt_app.name,
        "description": prompt_app.spec.get("description", ""),
        "variables": prompt_app.variables,
        "output_type": prompt_app.output_type,
    }


@app.get("/api/apps")
def apps():
    loaded = load_apps(APPS_DIR) if APPS_DIR.is_dir() else {"apps": {}, "problems": {}}

    return {
        "apps": [app_summary(item) for item in loaded["apps"].values()],
        "problems": loaded["problems"],
    }


@app.get("/api/apps/{name}")
def app_detail(name: str):
    prompt_app = load_app(name)

    return {"spec": prompt_app.spec, "variables": prompt_app.variables}


@app.post("/api/apps")
def save_app(request: AppSpecRequest):
    """Create or replace an app file from a spec."""

    prompt_app = build_app(request.spec)
    APPS_DIR.mkdir(parents=True, exist_ok=True)
    path = app_file(prompt_app.name)
    temporary = path.with_suffix(".json.tmp")

    temporary.write_text(
        json.dumps(prompt_app.spec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)

    return app_summary(prompt_app)


@app.delete("/api/apps/{name}")
def delete_app(name: str):
    path = app_file(name)

    if not path.is_file():
        raise HTTPException(status_code=404, detail="App not found.")

    path.unlink()

    return {"deleted": name}


@app.post("/api/apps/render")
def render_app(request: AppTestRequest):
    """Show the prompt an app would send, without calling any model."""

    prompt_app = build_app(request.spec)
    check_inputs(request.inputs)

    try:
        system, prompt = prompt_app.render(request.inputs)
    except AppError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None

    return {"system": system, "prompt": prompt, "variables": prompt_app.variables}


@app.post("/api/apps/test")
def test_app(request: AppTestRequest):
    """Run an unsaved spec. Failures are reported in the body, with the raw reply."""

    prompt_app = build_app(request.spec)
    runtime = resolve_runtime(request.runtime) if request.runtime else None

    return execute_app(
        prompt_app, request.inputs, runtime, request.temperature, request.max_tokens
    )


@app.post("/api/apps/{name}/run")
def run_app(name: str, request: AppRunRequest):
    """Run a saved app: the endpoint your own application can call."""

    prompt_app = load_app(name)
    runtime = resolve_runtime(request.runtime) if request.runtime else None

    outcome = execute_app(
        prompt_app, request.inputs, runtime, request.temperature, request.max_tokens
    )

    if not outcome["ok"]:
        status = 422 if outcome["kind"] == "input" else 502
        raise HTTPException(status_code=status, detail=outcome["error"])

    return {key: outcome[key] for key in ("output", "attempts", "runtime", "latency_ms")}


# ---------------------------------------------------------------------------
# OpenAI-compatible gateway
#
# Lets any application that already speaks the OpenAI chat API (in any
# language) use a workbench runtime by changing its base URL to
# http://<host>:<port>/v1. It covers non-streaming chat completions only.
# ---------------------------------------------------------------------------


class GatewayMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class GatewayRequest(BaseModel):
    model: Optional[str] = None
    messages: List[GatewayMessage] = Field(min_length=1, max_length=100)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4096)
    stream: Optional[bool] = False


def openai_error(status: int, message: str, error_type: str):
    return JSONResponse(
        status_code=status,
        content={"error": {"message": message, "type": error_type}},
    )


def gateway_auth_error(request: Request):
    """Return an error response unless the request carries the gateway key.

    The gateway is open unless ``NATLAS_GATEWAY_KEY`` is set. It has no other
    protection, so do not expose it to the internet without one.
    """

    key = os.getenv("NATLAS_GATEWAY_KEY")

    if not key:
        return None

    supplied = request.headers.get("authorization", "")

    if hmac.compare_digest(supplied.encode(), f"Bearer {key}".encode()):
        return None

    return openai_error(401, "Invalid or missing API key.", "invalid_request_error")


def gateway_runtime(model: Optional[str]) -> Optional[str]:
    """Map a model name to a runtime id; ``None`` means the default runtime."""

    model = (model or "").lower()

    if model in RUNTIMES:
        return model

    if model.startswith("natlas-") and model[len("natlas-"):] in RUNTIMES:
        return model[len("natlas-"):]

    return None


@app.get("/v1/models")
def gateway_models(request: Request):
    denied = gateway_auth_error(request)

    if denied:
        return denied

    ids = ["natlas"] + [
        f"natlas-{item['id']}"
        for item in runtimes()["runtimes"]
        if item["configured"]
    ]

    return {
        "object": "list",
        "data": [
            {"id": model, "object": "model", "owned_by": "natlas-workbench"}
            for model in ids
        ],
    }


@app.post("/v1/chat/completions")
def gateway_chat(request: Request, body: GatewayRequest):
    denied = gateway_auth_error(request)

    if denied:
        return denied

    if body.stream:
        return openai_error(
            400, "Streaming is not supported by this gateway.", "invalid_request_error"
        )

    messages = [m.model_dump() for m in body.messages]

    if messages[-1]["role"] != "user" or not messages[-1]["content"].strip():
        return openai_error(
            400,
            "The last message must be a non-empty user message.",
            "invalid_request_error",
        )

    runtime = gateway_runtime(body.model)

    try:
        result = run_chat(
            runtime,
            messages,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        )
    except Exception:
        logger.exception("Gateway chat request failed.")

        return openai_error(502, INFERENCE_FAILED, "api_error")

    return {
        "id": "chatcmpl-" + uuid.uuid4().hex[:24],
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.model or "natlas",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result["response"]},
                "finish_reason": "stop",
            }
        ],
        "x_natlas": {
            "runtime": result["runtime"],
            "latency_ms": result["latency_ms"],
        },
    }
