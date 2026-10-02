# N-ATLaS Browser Playground

The Browser Playground provides a developer-facing interface for interacting with N-ATLaS through the N-ATLaS Developer Workbench.

## Purpose

The playground will allow developers to:

- Enter prompts
- Select an N-ATLaS runtime
- Generate responses
- Inspect model responses
- View basic generation metadata
- Test different prompts interactively

## Architecture

```text
Browser
   ↓
Playground Backend
   ↓
N-ATLaS SDK
   ↓
N-ATLaS Runtime Adapter
   ↓
N-ATLaS