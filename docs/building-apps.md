# Building applications on N-ATLaS

This guide shows how to go from "I can send N-ATLaS a prompt" to a working application, using the
workbench's SDK, prompt apps, HTTP API, OpenAI-compatible gateway and starter projects.

> **Know your runtime.** The workbench does not host a model. It connects your application to a
> runtime you configure: a community Gradio Space, an OpenAI-compatible endpoint, or a local GGUF
> file. Availability, speed and answer quality depend on that runtime, not on this toolkit.

## 1. The pieces

| Piece | Use it when |
| --- | --- |
| **Python SDK** (`natlas_sdk`) | Your application is written in Python. |
| **Prompt apps** (`apps/*.json`) | You want a reusable task ("translate", "extract contact details") defined once and run from Python, the command line, the browser or HTTP. |
| **Gateway** (`/v1/chat/completions`) | Your application is in another language, or already uses an OpenAI client library. |
| **Workbench UI** | You are designing prompts, comparing runtimes, or checking behaviour before writing code. |
| **Starter projects** (`natlas new`) | You want a working skeleton to edit. |
| **Mock runtime** | You are developing or testing without a model. It echoes your prompt. |

## 2. Set up

```bash
git clone https://github.com/emmybaba/natlas-developer-workbench
cd natlas-developer-workbench
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[gradio,server,dev]"
```

Run the workbench with the offline mock runtime, then open <http://127.0.0.1:8000>:

```bash
NATLAS_RUNTIME=mock uvicorn playground.app:app --reload     # PowerShell: $env:NATLAS_RUNTIME = "mock"
```

For a real model, set the variables for your runtime (see the README, "Runtime options"), for example:

```bash
export NATLAS_RUNTIME=gradio
export NATLAS_GRADIO_BASE_URL=https://your-space.hf.space
```

In the UI, **Test runtime** confirms the service actually answers. "Configured" only means the
environment variables are set.

## 3. Recipes

### 3.1 One prompt, one answer

```python
from natlas_sdk import NAtlas

client = NAtlas(runtime_type="gradio", retries=2)
print(client.generate("Explain antimicrobial resistance in one sentence.",
                      system="Answer plainly.", temperature=0.2, max_tokens=150))
```

`system`, `temperature` and `max_tokens` are optional; leave them out to use the runtime's defaults.
`retries=2` re-tries transient failures (a sleeping Space, a dropped connection) with a growing
delay. It never retries bad input or missing configuration.

### 3.2 A chatbot that remembers

```python
chat = client.conversation(system="You are a helpful assistant. Keep answers short.")
print(chat.say("Hello"))
print(chat.say("And how would I say that in Yoruba?"))
chat.reset()
```

The conversation keeps its own history and trims the oldest messages once it passes `max_messages`
(default 40). If a call fails, the history is left unchanged so you can retry. Whether the model
uses earlier turns well depends on the runtime: the Gradio runtime sends the whole message list to
the Space, and the Space decides what to do with it.

### 3.3 A reusable task (prompt app)

A prompt app is a JSON file in `apps/`:

```json
{
  "name": "translator",
  "description": "Translate text into a Nigerian language.",
  "system": "You are a careful translator. Reply with the translation only.",
  "template": "Translate the following text into {{target_language}}:\n\n{{text}}",
  "inputs": [
    {"name": "target_language", "default": "Yoruba"},
    {"name": "text"}
  ],
  "output": {"type": "text"},
  "options": {"temperature": 0.2, "max_tokens": 400}
}
```

Design and try it in the **App Builder** tab, then use it anywhere:

```python
from natlas_sdk import NAtlas, PromptApp

app = PromptApp.from_file("apps/translator.json")
print(app.run(NAtlas(), {"text": "Good morning", "target_language": "Hausa"}).output)
```

```bash
python -m sdk.natlas_sdk run translator -i text="Good morning" -i target_language=Igbo
python -m sdk.natlas_sdk run translator -i text="Good morning" --show-prompt     # no model call
curl -s localhost:8000/api/apps/translator/run -H 'Content-Type: application/json' \
     -d '{"inputs": {"text": "Good morning"}}'
```

Values are inserted into the template once, so text containing `{{something}}` is never expanded.

### 3.4 Structured (JSON) output

Set `"output": {"type": "json", "keys": ["name", "phone", "location"]}` (see
`apps/contact-extractor.json`). The runner pulls the JSON out of the reply, even when the model adds
prose or code fences, checks the required keys, and asks the model to correct itself up to
`options.retries` times.

Models do not always comply. Always handle the failure:

```python
from natlas_sdk import OutputError

try:
    result = app.run(client, {"message": text})
    data = result.output
except OutputError as error:
    log(error, error.raw)        # error.raw is what the model actually said
```

### 3.5 Any language, or an existing OpenAI integration

The workbench serves `POST /v1/chat/completions` and `GET /v1/models`. Point an OpenAI client at
`http://127.0.0.1:8000/v1`:

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="not-needed")
reply = client.chat.completions.create(
    model="natlas",                      # or natlas-gradio, natlas-openai, natlas-llama_cpp, natlas-mock
    messages=[{"role": "user", "content": "Translate into Yoruba: Good morning"}],
)
print(reply.choices[0].message.content)
```

* `natlas` uses the workbench's default runtime (`NATLAS_RUNTIME`); `natlas-<runtime>` picks one.
  Any other model name also uses the default runtime.
* Supported: non-streaming chat completions with `messages`, `temperature` and `max_tokens`.
  **Not supported:** streaming (`stream: true` returns an error), tool calls, embeddings, multiple choices.
* Token usage is not reported.
* Set `NATLAS_GATEWAY_KEY` to require `Authorization: Bearer <key>`. Without it the gateway is open.

### 3.6 Start from a skeleton

```bash
natlas templates
natlas new chat-cli      ./my-chat        # terminal chat with memory
natlas new api-service   ./my-api         # FastAPI service: one endpoint per file in apps/
natlas new node-client   ./my-node        # Node.js script using the gateway
```

Each project has its own README. Python projects import `natlas_sdk`, which `pip install -e .` in the
workbench makes available.

## 4. Testing and quality

* **Develop against the mock runtime.** It is deterministic, so your application's tests do not depend
  on a remote service. It returns JSON when a prompt asks for JSON, which exercises structured-output code.
* **Write prompt suites** in `datasets/prompts/*.jsonl` and run them with
  `python -m evaluation datasets/prompts/my-suite.jsonl --runtime gradio`. Checks are simple assertions
  (non-empty, substrings, length, valid JSON); they do not score translation quality or accuracy.
  Have fluent speakers review outputs for the languages you ship.
* **Compare runtimes** in the Compare tab before choosing one.
* **Handle failures.** Network calls fail. Catch exceptions from `generate`/`chat`, show a useful message,
  and consider `retries`.

## 5. Before you go to production

The workbench is a development toolkit. Before real users depend on an application:

* A community Gradio Space is not a service you control. It can disappear, slow down or change.
  Use a runtime you operate or have an agreement with for anything important.
* The workbench server and the starter API have **no authentication, rate limiting or request logging**
  beyond the optional gateway key. Put them behind your own protections.
* There is no streaming, so long answers arrive all at once.
* Check the license and provenance of any model file you distribute.

## 6. Reference

**SDK**

| Call | Purpose |
| --- | --- |
| `NAtlas(runtime_type=..., retries=0)` | Create a client (`gradio`, `openai`, `llama_cpp`, `mock`) |
| `client.generate(prompt, system=, temperature=, max_tokens=)` | One prompt, one reply |
| `client.chat(messages, ...)` | Reply to a message list (`role`/`content`), last message from the user |
| `client.conversation(system=)` | Chat object with `.say()` and `.reset()` |
| `PromptApp.from_file(path).run(client, inputs)` | Run a prompt app; returns `.output`, `.raw`, `.attempts` |
| `extract_json(text)`, `generate_json(client, prompt, keys=[...])` | Structured output helpers |

**Workbench HTTP API:** `/api/runtimes`, `/api/generate`, `/api/chat`, `/api/compare`, `/api/apps`
(list, get, save, delete, `/api/apps/{name}/run`), `/api/datasets`, `/api/evaluate/case`, and the gateway
`/v1/models`, `/v1/chat/completions`.
