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
| `sdk/natlas_sdk/`              | Public Python SDK                                           |
| `playground/app.py`            | FastAPI backend for the browser playground                  |
| `playground/static/index.html` | Browser-based prompt interface                              |
| `tests/`                       | Automated and optional live-inference tests                 |
| `datasets/`                    | Dataset-related project area                                |
| `evaluation/`                  | Evaluation-related project area                             |
| `examples/`                    | Example application area                                    |
| `docs/`                        | Project documentation                                       |

Some directories establish the foundation for future functionality; their presence alone does not imply that a complete dataset-management, evaluation, or fine-tuning workflow is implemented.

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

## 4. Browser playground

The playground provides a web interface for submitting prompts to the configured runtime.

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
| `POST` | `/api/generate` | Submits a prompt to the configured runtime  |

Example generation request:

```json
{
  "prompt": "Explain antimicrobial resistance in one sentence."
}
```

Successful response format:

```json
{
  "response": "The generated model response appears here."
}
```

The generation endpoint rejects blank prompts and returns a controlled HTTP error if inference fails. A successful health check confirms that the application responds; it does not independently establish that the model service is available.

## 5. Configuration

For the community Gradio runtime, configure the endpoint in PowerShell:

```powershell
$env:NATLAS_GRADIO_BASE_URL = "https://koladeodunope-ednai-natlas-runtime.hf.space"
```

The environment variable applies to the current PowerShell session. Set it again in a new terminal, or configure environment variables through your deployment environment.

Do not commit API keys, credentials, private endpoints, or other secrets to GitHub.

## 6. Testing

Run the full automated test suite from the project root:

```powershell
pytest -q
```

Run the live Gradio inference test separately:

```powershell
pytest -s tests/test_gradio_live.py
```

The live test is skipped when `NATLAS_GRADIO_BASE_URL` is not configured.

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

These results establish that the tested integration worked at that time. They do not guarantee future availability of the third-party endpoint.

## 7. Current limitations

* The Gradio runtime depends on an externally managed community service.
* The OpenAI-compatible runtime requires a compatible inference endpoint.
* The local GGUF runtime requires a compatible model artifact and a working local inference installation.
* Runtime availability and inference success are different from application health.
* Dataset management, evaluation workflows, fine-tuning workflows, deployment automation, and production-grade observability should be treated as future work unless independently implemented and tested.
* The project has not established guaranteed uptime, production scalability, security certification, or a managed public inference service.

## 8. Development principles

The workbench follows these principles:

1. **Runtime abstraction:** keep application integrations separate from backend-specific inference details.
2. **Deployment neutrality:** allow developers to configure compatible inference backends without claiming that every backend is universally available.
3. **Testability:** test configuration, interface behavior, error handling, and live integration separately.
4. **Evidence-based documentation:** distinguish implemented code, observed test results, planned functionality, and external dependencies.
5. **Responsible model use:** check model licensing, provenance, access restrictions, and redistribution terms before distributing model files.

## 9. Repository

GitHub repository:

https://github.com/emmybaba/natlas-developer-workbench

## 10. Project status

N-ATLaS Developer Workbench is an evolving developer infrastructure project. Its current demonstrated capabilities include a Python SDK, configurable runtime integrations, a FastAPI browser playground, and successful tests against a community-hosted inference endpoint.

Further work is needed to make external inference more resilient, strengthen deployment and configuration documentation, and implement and verify additional developer workflows.

**The goal is to make N-ATLaS easier for developers to integrate and experiment with through a reusable, testable software interface.**
