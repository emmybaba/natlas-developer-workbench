# {{project_name}}

An HTTP service that turns N-ATLaS prompt apps into API endpoints.

## Set up

```bash
pip install -r requirements.txt
pip install -e /path/to/natlas-developer-workbench[gradio]
```

## Run

```bash
uvicorn app:app --reload                       # offline mock runtime
NATLAS_RUNTIME=gradio NATLAS_GRADIO_BASE_URL=https://your-space.hf.space uvicorn app:app
```

```bash
curl -s localhost:8000/apps
curl -s localhost:8000/apps/translator/run \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"text": "Good morning", "target_language": "Hausa"}}'
```

## Customise

* Each file in `apps/` is a prompt app: a prompt template with `{{variables}}`, a system
  instruction, and an output type (`text` or `json`). Design and test them in the
  workbench's App Builder tab, then save the JSON here.
* A file's `name` must match its file name (`apps/translator.json` -> `translator`).
* Run `pytest` to check the service (tests use the mock runtime).

Before exposing this service beyond your own machine, add authentication and rate
limiting. This starter has neither.
