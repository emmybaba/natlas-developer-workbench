# N-ATLaS Developer Workbench

**A developer infrastructure toolkit for integrating, testing, and experimenting with N-ATLaS inference runtimes.**

N-ATLaS Developer Workbench is a Python-based developer toolkit designed to simplify access to N-ATLaS inference through a runtime abstraction, Python SDK, configurable adapters, and a browser-based playground.

The project separates application code from the underlying inference service so developers can work with different runtime backends without tying their applications to one deployment environment.

> **Project status:** In progress. Live inference through the Python runtime and browser playground has been tested successfully against a third-party community Gradio Space. The external service is not controlled by this project.

## 1. Project objectives

The workbench aims to provide developers with:

* A common interface for sending prompts to configured N-ATLaS runtimes.
* A Python SDK for integrating inference into Python applications.
* Runtime abstraction for different inference deployment approaches.
* A browser playground for interactive prompt testing.
* Automated tests for configuration, SDK behavior, API endpoints, and runtime contracts.
* A foundation for future evaluation, dataset, and model-development workflows.

## 2. Architecture

The current implementation includes the following components:

| Component                      | Purpose                                                     |
| ------------------------------ | ----------------------------------------------------------- |
| `adapter/natlas/`              | N-ATLaS connection configuration and adapter functionality  |
| `runtime/base.py`              | Abstract runtime interface                                  |
| `runtime/gradio.py`            | Integration with a Gradio-hosted inference service          |
| `runtime/openai_compatible.py` | Integration with an OpenAI-compatible inference endpoint    |
| `runtime/llama_cpp.py`         | Local GGUF inference integration through `llama-cpp-python` |
| `runtime/mock.py`              | Offline mock runtime for development without a model        |
| `sdk/natlas_sdk/`              | Public Python SDK                                           |
| `playground/app.py`            | FastAPI backend for the workbench                           |
| `playground/static/index.html` | Browser workbench: Playground, Compare and Evaluate tabs    |
| `sdk/natlas_sdk/`              | Python SDK: generate, chat, conversations, prompt apps, JSON output, retries |
| `apps/`                        | Prompt apps: reusable tasks defined as JSON                 |
| `scaffold/`                    | `natlas new` project generator and starter templates        |
| `docs/building-apps.md`        | Developer guide for building applications                   |
| `evaluation/`                  | Prompt-suite runner and command-line interface              |
| `datasets/prompts/`            | JSONL prompt suites (see `datasets/README.md`)              |
| `examples/quickstart.py`       | Minimal SDK usage example                                   |
| `tests/`                       | Automated and optional live-inference tests                 |

The evaluation runner executes simple deterministic checks over prompt suites. Dataset management beyond those JSONL files, scored evaluation of model quality, and fine-tuning workflows are not implemented and remain future work.

### Request flow

1. A developer enters a prompt in the browser playground or calls the Python SDK.
2. The playground sends the prompt to the FastAPI backend.
3. The SDK selects or receives the configured runtime.
4. The runtime communicates with its configured inference service.
5. The response returns through the backend to the browser.

## 3. Runtime options

### Gradio runtime

The Gradio runtime communicates with a configured Gradio-hosted inference service.

Configuration variable:

`NATLAS_GRADIO_BASE_URL`

A community Space used during testing was:

`https://koladeodunope-ednai-natlas-runtime.hf.space`

This is a **third-party community endpoint**, not an official NCAIR-hosted service. It may become unavailable, change behavior, or stop accepting inference requests.

### OpenAI-compatible runtime

The OpenAI-compatible runtime uses the OpenAI Python client against a configured compatible endpoint.

This requires an endpoint that actually implements the expected API. The existence of this adapter does not imply that an official N-ATLaS OpenAI-compatible API is available.

Configuration variables:

* `NATLAS_BASE_URL`
* `NATLAS_API_KEY`
* `NATLAS_MODEL`

### Local GGUF runtime

The local runtime uses `llama-cpp-python` to load a compatible GGUF model file.

Configuration variables:

* `NATLAS_RUNTIME=llama_cpp`
* `NATLAS_MODEL_PATH`
* `NATLAS_N_CTX`
* `NATLAS_N_GPU_LAYERS`

A compatible model file and a working `llama-cpp-python` installation are required. Hardware, memory, operating-system support, model format, and installation options affect whether local inference will work.

A third-party model artifact considered for this workflow is `inuwamobarak/N-ATLaS-8B-GGUF-Q4_K_M`. It should not be represented as an official NCAIR model distribution. Verify its license and provenance before redistribution.

### Mock runtime

`mock` (set `NATLAS_RUNTIME=mock`, or pick it in the UI) performs no inference. It echoes the prompt and the options it received (and returns a placeholder JSON object when a prompt asks for JSON), so you can develop and demo the workbench, the SDK and the evaluation runner with no model or network. Content checks such as `expect_any` or `expect_json` will fail against it by design.

## 4. Building applications

The workbench is meant for developers building applications on N-ATLaS. Read **[docs/building-apps.md](docs/building-apps.md)** for the full guide. In short:

```bash
pip install -e ".[gradio,server,dev]"          # makes `natlas_sdk` and the `natlas` command available
natlas new api-service ./my-api                 # or: chat-cli, node-client
```

```python
from natlas_sdk import NAtlas

client = NAtlas(runtime_type="gradio", retries=2)
chat = client.conversation(system="Keep answers short.")
print(chat.say("Hello"))
```

* **Prompt apps** (`apps/*.json`) define a task once and run from Python, the command line (`python -m sdk.natlas_sdk run translator -i text="Good morning"`), the browser, or HTTP (`POST /api/apps/{name}/run`).
* **OpenAI-compatible gateway** (`/v1/chat/completions`, `/v1/models`) lets code in any language, or an existing OpenAI client, use a workbench runtime by changing its base URL. It supports non-streaming chat only. Set `NATLAS_GATEWAY_KEY` to require a bearer token; without it the gateway is open.
* **Starter projects** (`natlas templates`, `natlas new <template> <dir>`): a terminal chat, a FastAPI service built from your prompt apps, and a Node.js client.
* **Retries:** `NAtlas(retries=2)` or `NATLAS_RETRIES` retries runtime failures with growing delays; invalid input and missing configuration are never retried.

The workbench has no authentication or rate limiting of its own beyond the optional gateway key. Do not expose it to the internet as it is.

## 5. Browser workbench

The workbench is a web interface with five tabs and a settings column:

* **Playground:** send a prompt to the selected runtime and see the response, latency and length. Includes ready-to-copy snippets (Python SDK, curl, OpenAI client and JavaScript through the gateway) for the current settings, example presets (English, Yoruba, Hausa, Igbo, Pidgin), and a history kept in your browser's local storage.
* **Chat:** a multi-turn conversation with the selected runtime.
* **App Builder:** design a reusable prompt app (template with `{{variables}}`, system instruction, text or JSON output), test it, save it to `apps/`, and copy the code to run it from your application.
* **Compare:** send one prompt to two to four runtimes at once and view the outputs side by side. A runtime that fails shows its own error without hiding the others.
* **Evaluate:** run a prompt suite from `datasets/prompts/` against the selected runtime, case by case with live progress, a Stop button, pass/fail checks, and a JSON report export.
* **Settings:** runtime, optional system instruction, temperature (0–2) and max tokens (1–4096). Blank values use the runtime's own defaults.

A runtime shown as configured only means its environment variables are set. Use **Test runtime** to check the service actually responds.

For the Gradio runtime, a system instruction is prepended to the user message, because the community Space's handling of a system role has not been verified. The OpenAI-compatible and local GGUF runtimes send it as a system message.

### Start the application

Activate the project's Python virtual environment, configure a working runtime, and run:

```powershell
uvicorn playground.app:app --reload
```

Open:

`http://127.0.0.1:8000`

The development server must remain running while using the page.

### Available endpoints

| Method | Endpoint        | Purpose                                     |
| ------ | --------------- | ------------------------------------------- |
| `GET`  | `/`             | Serves the browser playground               |
| `GET`  | `/api/health`   | Returns a basic application health response |
| `GET`  | `/api/runtimes` | Lists runtimes and whether their environment variables are set |
| `POST` | `/api/generate` | Submits a prompt to a runtime (default or chosen) |
| `POST` | `/api/compare`  | Sends one prompt to 2–4 runtimes, returns each outcome |
| `POST` | `/api/chat`     | Continues a multi-turn conversation |
| `GET`/`POST`/`DELETE` | `/api/apps` ... | List, read, save, delete and run prompt apps (`POST /api/apps/{name}/run`) |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat (non-streaming) |
| `GET`  | `/v1/models`    | OpenAI-compatible model list |
| `GET`  | `/api/datasets` | Lists prompt suites |
| `GET`  | `/api/datasets/{name}` | Returns the cases of one suite |
| `POST` | `/api/evaluate/case` | Runs and checks one case from a suite, or an inline case |

Example generation request (only `prompt` is required):

```json
{
  "prompt": "Explain antimicrobial resistance in one sentence.",
  "runtime": "gradio",
  "system": "Answer in one sentence.",
  "temperature": 0.2,
  "max_tokens": 200
}
```

Successful response format:

```json
{
  "response": "The generated model response appears here.",
  "runtime": "gradio",
  "latency_ms": 1840
}
```

`/api/compare` takes the same options plus `"runtimes": ["mock", "gradio"]` and returns `{"results": [{"ok": true, "runtime": "...", "response": "...", "latency_ms": 12}, {"ok": false, "runtime": "...", "error": "..."}]}`.

The generation endpoint rejects blank prompts and returns a controlled HTTP error if inference fails. A successful health check confirms that the application responds; it does not independently establish that the model service is available.

## 6. Configuration

For the community Gradio runtime, configure the endpoint in PowerShell:

```powershell
$env:NATLAS_GRADIO_BASE_URL = "https://koladeodunope-ednai-natlas-runtime.hf.space"
```

The environment variable applies to the current PowerShell session. Set it again in a new terminal, or configure environment variables through your deployment environment.

Do not commit API keys, credentials, private endpoints, or other secrets to GitHub.

### Evaluate from the command line

```powershell
python -m evaluation datasets/prompts/smoke.jsonl --runtime mock
python -m evaluation datasets/prompts/nigerian-languages.jsonl --runtime gradio --out report.json
```

The command exits with status 1 when any case fails or errors, so it can be used in scripts. See `datasets/README.md` for the suite format and what the checks do and do not measure.

## 7. Testing

Run the full automated test suite from the project root:

```powershell
pytest -q
```

Run the live Gradio inference test separately:

```powershell
pytest -s tests/test_gradio_live.py
```

The live test is skipped when `NATLAS_GRADIO_BASE_URL` is not configured.

New tests cover the mock runtime, SDK options and retries, prompt apps, the evaluation runner and bundled suites, the scaffold generator, and the API endpoints including the gateway (`tests/test_mock_runtime.py`, `tests/test_apps.py`, `tests/test_evaluation.py`, `tests/test_scaffold.py`, `tests/test_playground.py`).

### Recorded verification results

The following checks were observed during development:

* The FastAPI application imported successfully.
* The playground HTML endpoint returned HTTP 200.
* The health endpoint returned HTTP 200.
* Blank prompts were rejected with HTTP 422.
* The inference-failure path returned a controlled HTTP 502 response.
* The earlier full test suite completed with **8 passed, 1 skipped**.
* The live Gradio test subsequently completed with **1 passed in 7.27 seconds**, returning a non-empty model response.
* A browser playground request subsequently returned a coherent answer to an antimicrobial-resistance prompt.

Those results predate the workbench additions above. Run `pytest -q` to re-verify the current code.

These results establish that the tested integration worked at that time. They do not guarantee future availability of the third-party endpoint.

## 8. Current limitations

* The Gradio runtime depends on an externally managed community service.
* The OpenAI-compatible runtime requires a compatible inference endpoint.
* The local GGUF runtime requires a compatible model artifact and a working local inference installation.
* Runtime availability and inference success are different from application health.
* Dataset management, evaluation workflows, fine-tuning workflows, deployment automation, and production-grade observability should be treated as future work unless independently implemented and tested.
* The project has not established guaranteed uptime, production scalability, security certification, or a managed public inference service.

## 9. Development principles

The workbench follows these principles:

1. **Runtime abstraction:** keep application integrations separate from backend-specific inference details.
2. **Deployment neutrality:** allow developers to configure compatible inference backends without claiming that every backend is universally available.
3. **Testability:** test configuration, interface behavior, error handling, and live integration separately.
4. **Evidence-based documentation:** distinguish implemented code, observed test results, planned functionality, and external dependencies.
5. **Responsible model use:** check model licensing, provenance, access restrictions, and redistribution terms before distributing model files.

## 10. Repository

GitHub repository:

https://github.com/emmybaba/natlas-developer-workbench

## 11. Project status

N-ATLaS Developer Workbench is an evolving developer infrastructure project. Its current demonstrated capabilities include a Python SDK, configurable runtime integrations, a FastAPI browser playground, and successful tests against a community-hosted inference endpoint.

Further work is needed to make external inference more resilient, strengthen deployment and configuration documentation, and implement and verify additional developer workflows.

**The goal is to make N-ATLaS easier for developers to integrate and experiment with through a reusable, testable software interface.**
