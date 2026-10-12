"""{{project_name}}: an HTTP API for your N-ATLaS prompt apps.

Every JSON file in ./apps becomes an endpoint:  POST /apps/<name>/run
Edit or add files in ./apps (you can design them in the workbench's App Builder).
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from natlas_sdk import AppError, NAtlas, OutputError, load_apps

APPS_DIR = Path(os.getenv("APPS_DIR", Path(__file__).parent / "apps"))

app = FastAPI(title="{{project_name}}")
client = NAtlas(runtime_type=os.getenv("NATLAS_RUNTIME", "mock"), retries=2)
loaded = load_apps(APPS_DIR)


class RunRequest(BaseModel):
    inputs: dict = {}


@app.get("/health")
def health():
    return {"status": "ok", "apps": sorted(loaded["apps"]), "problems": loaded["problems"]}


@app.get("/apps")
def list_apps():
    return {
        name: {"description": item.spec.get("description", ""), "inputs": item.variables}
        for name, item in loaded["apps"].items()
    }


@app.post("/apps/{name}/run")
def run(name: str, request: RunRequest):
    prompt_app = loaded["apps"].get(name)

    if prompt_app is None:
        raise HTTPException(status_code=404, detail="Unknown app.")

    try:
        result = prompt_app.run(client, request.inputs)
    except AppError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except OutputError:
        raise HTTPException(
            status_code=502, detail="The model did not return usable output."
        ) from None
    except Exception:
        raise HTTPException(status_code=502, detail="Inference failed.") from None

    return {"output": result.output, "attempts": result.attempts}
