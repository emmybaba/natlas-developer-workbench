# {{project_name}}

A terminal chat built on the N-ATLaS Developer Workbench SDK.

## Set up

Install the workbench SDK once (from your clone of the workbench repository):

```bash
pip install -e /path/to/natlas-developer-workbench[gradio]
```

## Run

```bash
python main.py                      # offline mock runtime, no model needed
NATLAS_RUNTIME=gradio NATLAS_GRADIO_BASE_URL=https://your-space.hf.space python main.py
```

On Windows PowerShell set variables with `$env:NATLAS_RUNTIME = "gradio"`.

## Make it yours

* Change the assistant's behaviour with `SYSTEM_PROMPT`.
* `chat.say(text)` keeps history for you; `chat.reset()` clears it.
* For structured output or reusable tasks, see the `api-service` template and the
  workbench's developer guide (`docs/building-apps.md`).

Model quality and availability depend on the runtime you point this at.
