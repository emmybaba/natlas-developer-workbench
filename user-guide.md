# Tutorial: from zero to a working N-ATLaS application

This tutorial follows one developer's journey with the N-ATLaS Developer Workbench. You will install it,
explore it without a model, connect a real N-ATLaS runtime, design a reusable task (an English-to-Yoruba
translator for school children), test and improve it, and turn it into a small web service.

**Time:** about 60–90 minutes. **You need:** Python 3.10+, Git, and (optional) Node.js 18+.
Commands are for Windows PowerShell; macOS/Linux equivalents are noted where they differ.

> **Read this first.** The workbench does not host a model. It connects your code to a *runtime* you
> configure: a community Gradio Space, an OpenAI-compatible endpoint, or a local GGUF file. Speed,
> availability and answer quality come from that runtime. The bundled Gradio Space is a third-party
> service that can be slow, change or disappear. Language output, especially for Yoruba, Hausa and
> Igbo, must be reviewed by a fluent speaker before real users depend on it.

## The journey at a glance

| Stage | You do | You get |
| --- | --- | --- |
| 1. Install | Clone, create a virtual environment, install, run tests | A working toolkit |
| 2. Explore | Start the workbench on the offline **mock** runtime | Confidence in the tools, no model needed |
| 3. Connect | Point it at a real runtime and test it | Real N-ATLaS answers |
| 4. Design | Build a **prompt app** in the App Builder | A reusable task saved as JSON |
| 5. Improve | Add examples, write tests, compare | Better, measurable output |
| 6. Use | Call the app from Python, the command line and HTTP | The task inside your own code |
| 7. Ship | Generate a starter project, add a client | A small service others can call |

---

## Stage 1: Install

```powershell
git clone https://github.com/emmybaba/natlas-developer-workbench
cd natlas-developer-workbench
python -m venv .venv
.venv\Scripts\Activate.ps1                  # macOS/Linux: source .venv/bin/activate
pip install -e ".[gradio,server,dev]"
pytest -q
```

`pip install -e .` makes the `natlas_sdk` package and the `natlas` command available everywhere in this
environment. You should see all tests pass; the live Gradio test is skipped until you configure a runtime.

If activation is blocked on Windows, run `Set-ExecutionPolicy -Scope Process RemoteSigned` and try again.

## Stage 2: Explore with no model (mock runtime)

Environment variables last only for the terminal session where you set them. Set them again in every new terminal.

```powershell
$env:NATLAS_RUNTIME = "mock"                # macOS/Linux: export NATLAS_RUNTIME=mock
uvicorn playground.app:app --reload
```

Open <http://127.0.0.1:8000>. The mock runtime only **echoes** your prompt back, which is exactly what you
want while learning the tools: it is instant, free and never changes.

Take a tour:

1. **Playground:** pick a preset, click **Generate**. Look at the response, the time, and the
   **Use this in code** box. It writes ready-to-copy snippets (Python SDK, curl, OpenAI client, JavaScript).
2. **Chat:** send two messages in a row. The history is kept, so the second reply knows about the first
   (the mock shows `(turn 2)`).
3. **Compare:** choose two runtimes and send one prompt to both. A runtime that fails shows its own error.
4. **Evaluate:** run the `smoke` suite. Every case should pass.

Things that confuse newcomers:

* The prompt box sends its contents to the model **as the prompt**. Don't paste JSON or code there.
* A runtime marked "not configured" has no environment variables set. Choose another runtime or set them.
* "Configuration found" does not mean the service works. Click **Test runtime** to find out.

## Stage 3: Connect a real runtime

Stop the server (`Ctrl+C`), then set the variables for the runtime you will use.

**Community Gradio Space**

```powershell
$env:NATLAS_RUNTIME = "gradio"
$env:NATLAS_GRADIO_BASE_URL = "https://koladeodunope-ednai-natlas-runtime.hf.space"
uvicorn playground.app:app --reload
```

**OpenAI-compatible endpoint** you have access to: `NATLAS_BASE_URL`, `NATLAS_API_KEY`, `NATLAS_MODEL`.
**Local GGUF model:** `NATLAS_RUNTIME=llama_cpp`, `NATLAS_MODEL_PATH` (needs a compatible model file and
`llama-cpp-python`). Check the licence and provenance of any model file you use.

In the page choose the runtime and click **Test runtime**. A reply with a time in milliseconds means it
works. The first call to a sleeping Space can take 10–20 seconds; later calls are usually quicker.

Try a real prompt in the Playground: `Translate into Yoruba: Good morning, how are you?` Clear the
**System instruction** box first if it has leftover text.

Confirm from the command line too (this also runs the live test):

```powershell
pytest -s tests/test_gradio_live.py
```

## Stage 4: Design a prompt app

A **prompt app** is one reusable task, stored as a JSON file in `apps/`: a prompt template with
`{{variables}}`, an optional system instruction, an output type, and default settings. You design it in the
browser, then run the same file from Python, the command line or HTTP.

In the **App Builder** tab, click **New app** and fill in:

| Field | Value |
| --- | --- |
| Name | `yoruba-school-translator` (lowercase letters, digits, hyphens) |
| Description | `Translate English into simple Yoruba for school children.` |
| System instruction | `You are a patient translator for primary school children. Use simple, clear Yoruba with correct tone marks. Reply with the translation only.` |
| Prompt template | `Translate into Yoruba:` then a blank line, then `{{text}}` |
| Output | Plain text |
| Temperature / Max tokens | `0.2` / `300` |

Rules that trip people up:

* The template **must contain** `{{text}}`. Without it the page says "This template has no variables" and
  there is nothing to fill in.
* Each `{{name}}` becomes a test input box. Type a sentence there, choose the real runtime, click **Run test**.
* **Preview prompt** shows exactly what would be sent, without calling a model.
* Click **Save app**. The file is created at `apps/yoruba-school-translator.json`. The file name always
  matches the **Name**.

Check it exists:

```powershell
dir apps
```

## Stage 5: Test and improve

### 5a. Judge the output with a fluent speaker

Run several sentences and record what is wrong: missing tone marks, stiff phrasing, words too hard for
children, English words left in. Models vary from call to call, so keep **Temperature** at or below `0.2`.

### 5b. Teach by example

Models copy the style of examples. Put your own **corrected** translations into the template (replace the
placeholders below with sentences and Yoruba a fluent speaker has approved):

```
Translate English into Yoruba. Follow the style of these examples.

English: <approved English sentence 1>
Yoruba: <approved Yoruba 1>

English: <approved English sentence 2>
Yoruba: <approved Yoruba 2>

English: {{text}}
Yoruba:
```

Paste it into the **Prompt template** box and save. Don't write `{{` anywhere except the `{{text}}` placeholder.

### 5c. Turn corrections into tests

Create `datasets/prompts/yoruba-school.jsonl`, one JSON object per line:

```json
{"id": "greeting-class", "prompt": "Translate into Yoruba: Good morning, class.", "tags": ["yoruba", "school"], "expect_any": ["<a word that must appear>"]}
{"id": "sit-down", "prompt": "Translate into Yoruba: Please sit down.", "tags": ["yoruba", "school"]}
```

Add `expect_any` / `expect_contains` only where you are sure of the words. Run it:

```powershell
python -m evaluation datasets/prompts/yoruba-school.jsonl --runtime gradio --out report.json
```

Or open the **Evaluate** tab, choose the suite, and click **Run suite** to watch results arrive one by
one, expand any case to read the response, and export a report. Re-run after every prompt change.

> These checks are simple assertions (non-empty, contains, length, valid JSON). They do **not** score
> translation quality. Cases without expectations only confirm the runtime answers; a person reads the
> output.

### 5d. Compare runtimes

If you have more than one runtime configured, use **Compare** to send the same prompt to each and
choose with evidence.

## Stage 6: Use the app in your own code

**Command line**

```powershell
python -m sdk.natlas_sdk run yoruba-school-translator -i text="Good morning, children. Please sit down."
python -m sdk.natlas_sdk run yoruba-school-translator -i text="Hello" --show-prompt   # no model call
```

**Python**

```python
from natlas_sdk import NAtlas, PromptApp

client = NAtlas(runtime_type="gradio", retries=2)       # retries a sleeping Space, never bad input
app = PromptApp.from_file("apps/yoruba-school-translator.json")
print(app.run(client, {"text": "Good morning, class."}).output)
```

**HTTP**, while the workbench is running:

```powershell
curl.exe -s http://127.0.0.1:8000/api/apps/yoruba-school-translator/run `
  -H "Content-Type: application/json" `
  -d '{\"inputs\": {\"text\": \"Good morning, class.\"}}'
```

Other building blocks in the SDK:

```python
chat = client.conversation(system="Answer briefly.")     # multi-turn memory
print(chat.say("Hello"))
print(chat.say("And in Yoruba?"))
```

Apps with `"output": {"type": "json", "keys": [...]}` return structured data and ask the model to correct
itself if the JSON is unusable. Always handle `OutputError`; models do not always comply
(see `apps/contact-extractor.json` and [building-apps.md](building-apps.md)).

## Stage 7: Ship a small service

Generate a starter project next to the workbench:

```powershell
natlas templates
natlas new api-service ..\yoruba-school-app
copy apps\yoruba-school-translator.json ..\yoruba-school-app\apps\
cd ..\yoruba-school-app
pip install -r requirements.txt
$env:NATLAS_RUNTIME = "gradio"
$env:NATLAS_GRADIO_BASE_URL = "https://koladeodunope-ednai-natlas-runtime.hf.space"
uvicorn app:app --reload --port 8001
```

(Use `--port 8001` if the workbench is still running on 8000.) Every JSON file in its `apps/` folder is an
endpoint:

```powershell
curl.exe -s http://127.0.0.1:8001/apps
curl.exe -s http://127.0.0.1:8001/apps/yoruba-school-translator/run `
  -H "Content-Type: application/json" `
  -d '{\"inputs\": {\"text\": \"Good morning, class.\"}}'
```

Run `pytest` in that folder to check the service (its tests use the mock runtime).

**Calling from other languages.** The workbench also serves an OpenAI-compatible endpoint at
`http://127.0.0.1:8000/v1`, so code in any language, or an existing OpenAI client, can use it:

```powershell
natlas new node-client ..\my-node-client
cd ..\my-node-client
$env:NATLAS_BASE_URL = "http://127.0.0.1:8000/v1"
node chat.mjs "Translate into Yoruba: Good morning"
```

The gateway supports non-streaming chat only. Set `NATLAS_GATEWAY_KEY` on the workbench to require
`Authorization: Bearer <key>`; without it the gateway is open.

Other starters: `natlas new chat-cli <dir>` is a terminal chat with memory.

### Before real users depend on it

- [ ] A fluent speaker has reviewed outputs, including edge cases and long sentences.
- [ ] You use a runtime you control or have an agreement with. A community Space can vanish.
- [ ] Failures are handled: catch exceptions, show a friendly message, use `retries`.
- [ ] You added authentication and rate limiting. The starters have neither beyond the optional gateway key.
- [ ] Nothing exposes the workbench to the internet as it is.
- [ ] No keys or private endpoints are committed (`.env` is ignored by Git).
- [ ] You checked the licence and provenance of any model you distribute.
- [ ] Your prompt tests run before every release.

---

## Troubleshooting

| What you see | Cause and fix |
| --- | --- |
| Runtime dropdown shows "(not configured)" or **Test runtime** says to set variables | That runtime's environment variables are missing. Set them in the terminal that runs `uvicorn`, restart, or choose **Mock**. |
| Variables seem to vanish | They last for one terminal session. Set them again in each new terminal. |
| Responses are `[mock runtime] Echo: ...` | You are on the mock runtime. Choose the real one. |
| First request takes 10–20 s | A sleeping Space is waking up. Retry; use `retries=2` in code. |
| "Inference failed. Check the runtime configuration..." | The runtime errored or is unreachable. Check **Test runtime**, the variables, and the server's terminal for the logged error. |
| The "translation" is nonsense about JSON | You pasted JSON into the Prompt box. App definitions go in `apps/` or the App Builder. |
| "This template has no {{variables}}" | Add a placeholder such as `{{text}}` to the template. |
| App missing from **Saved apps** | The file name must equal the `name` inside it, with lowercase letters, digits and hyphens. Check `dir apps`, then refresh. |
| `Missing input(s): text` | The app needs a value for `text`. Pass `-i text="..."` or `{"inputs": {"text": "..."}}`. |
| `natlas` is not recognised | Activate the virtual environment and run `pip install -e ".[gradio,server,dev]"` again. |
| Port already in use | Another server is running. Stop it or add `--port 8001`. |
| Git warns "LF will be replaced by CRLF" | Harmless line-ending notice on Windows. |
| `git status` lists files you didn't edit | Usually line endings. Check with `git diff --ignore-cr-at-eol --stat`; if empty, `git restore <file>`. |

## Where to go next

* [building-apps.md](building-apps.md): concepts, recipes and a reference for the SDK and HTTP API.
* [../datasets/README.md](../datasets/README.md): the test-suite format.
* `apps/`: examples of text and JSON prompt apps.
* The **Chat** tab and `client.conversation()` for assistants that keep context.
