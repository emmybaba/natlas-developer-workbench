# {{project_name}}

Calls N-ATLaS from Node.js through the workbench's OpenAI-compatible gateway. Any language
or framework that can talk to the OpenAI chat API can use the same URL.

## Run

1. Start the workbench (in its own folder): `uvicorn playground.app:app`
   (use `NATLAS_RUNTIME=mock` to try it without a model).
2. Then:

```bash
node chat.mjs "Translate into Yoruba: Good morning"
```

Environment variables: `NATLAS_BASE_URL` (default `http://127.0.0.1:8000/v1`),
`NATLAS_MODEL` (`natlas`, or `natlas-gradio`, `natlas-openai`, `natlas-llama_cpp`, `natlas-mock`),
`NATLAS_API_KEY` (only if the workbench sets `NATLAS_GATEWAY_KEY`).

The gateway supports non-streaming chat completions only.
