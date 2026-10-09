import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from sdk.natlas_sdk import NAtlas


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


app = FastAPI(
    title="N-ATLaS Developer Workbench",
    description="Browser Playground backend for N-ATLaS",
    version="0.1.0",
)


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    response: str


@app.get("/")
def playground():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "N-ATLaS Developer Workbench",
    }


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    prompt = request.prompt.strip()

    if not prompt:
        raise HTTPException(
            status_code=422,
            detail="Prompt must not be empty.",
        )

    try:
        client = NAtlas()
        response = client.generate(prompt)

        return GenerateResponse(response=response)

    except Exception:
        logger.exception("N-ATLaS inference request failed.")

        raise HTTPException(
            status_code=502,
            detail=(
                "Inference failed. Check the runtime configuration "
                "and inference service availability."
            ),
        ) from None