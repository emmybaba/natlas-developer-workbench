from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from sdk.natlas_sdk import NAtlas


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
    client = NAtlas()

    response = client.generate(request.prompt)

    return GenerateResponse(
        response=response,
    )