N-ATLaS DEVELOPER WORKBENCH
Technical Documentation
Project Repository: https://github.com/emmybaba/natlas-developer-workbench
Project Category: AI Developer Infrastructure / Language Model Application Development Toolkit
Project Status: In Progress — Hosted inference verified; local GGUF runtime configuration pending.
Documentation Date: 12 October 2026
________________________________________
1. Executive Summary
The N-ATLaS Developer Workbench is a Python-based developer infrastructure toolkit designed to simplify the development, testing, and integration of applications powered by N-ATLaS, a Nigerian language-model initiative.
Rather than functioning merely as a conversational chatbot, the Workbench provides a foundation through which developers can connect to configured inference services, send prompts programmatically, inspect model responses, and experiment with application workflows using a common software interface.
The system incorporates a Python Software Development Kit (SDK), a runtime abstraction layer, a FastAPI backend, and a browser-based developer playground. Its architecture separates application logic from the underlying inference service, enabling developers to work with different runtime configurations without having to redesign their application around a single deployment method.
Three inference approaches are represented in the project:
1.	Hosted inference through a Gradio endpoint.
2.	Inference through an OpenAI-compatible API, including a locally implemented gateway that forwards requests to the hosted Gradio service.
3.	Local inference using a compatible GGUF model through llama-cpp-python, currently undergoing configuration and testing.
During development, the hosted Gradio route and the OpenAI-compatible route were successfully tested. The browser playground returned generated text from a Yoruba translation prompt through the OpenAI-compatible route. The local GGUF runtime remains a work in progress pending completion of the model download and direct inference testing.
The Workbench is intended to reduce the technical barriers involved in moving from access to a language model to the development of practical software applications using that model.
2. Background and Problem Statement
Access to a language model is only one part of application development. Developers also need tools for connecting to the model, managing runtime configuration, sending requests, receiving responses, testing prompts, and incorporating model capabilities into application code.
Without a consistent integration layer, developers may need to write different connection logic for different inference services. This increases development effort and makes applications more dependent on specific deployment arrangements.
The N-ATLaS Developer Workbench addresses this challenge by introducing a common interface between application code and configured N-ATLaS inference runtimes.
The project focuses on developer enablement: helping software developers experiment with N-ATLaS and build application prototypes through reusable software components, a browser playground, and documented integration patterns.
3. Project Aim and Objectives
3.1 Aim
To develop an extensible software toolkit that simplifies the integration, testing, and application-level use of N-ATLaS through a common SDK, configurable inference runtimes, and an interactive developer playground.
3.2 Specific objectives
The project aims to:
1.	Provide a consistent Python interface for interacting with configured N-ATLaS inference services.
2.	Abstract runtime-specific connection details from application code.
3.	Provide a browser-based environment for testing prompts and examining generated responses.
4.	Support integration with hosted Gradio inference services.
5.	Support compatible OpenAI-style API endpoints through a dedicated runtime adapter.
6.	Establish a local inference option through GGUF and llama.cpp, subject to model and hardware compatibility.
7.	Provide a foundation for reusable application examples, automated tests, and developer documentation.
8.	Create an extensible architecture for future application scaffolding and model-evaluation workflows.
4. System Architecture
The Workbench separates the developer interface, application backend, SDK, runtime adapters, and inference service.
4.1 Verified hosted-inference architecture
The successfully tested OpenAI-compatible request path is:
Browser Playground → FastAPI Backend → Python SDK → OpenAI-Compatible Runtime → Local Gateway → Hosted Gradio Service → N-ATLaS Inference
The local gateway translates OpenAI-style chat-completion requests into requests accepted by the configured Gradio service. The hosted service performs the inference and returns generated text through the gateway to the SDK and browser.
The direct Gradio runtime is an alternative route that bypasses the OpenAI-compatible gateway.
4.2 Planned local-inference architecture
The local GGUF route follows a different request path:
Browser Playground → FastAPI Backend → Python SDK → llama.cpp Runtime → Local GGUF Model
This path is intended to load the model from local storage. It does not require the hosted Gradio service or the OpenAI-compatible gateway once correctly configured.
The architecture for local inference is represented in the project, and the llama-cpp-python package has been installed successfully. However, the GGUF model download and end-to-end local inference test are still pending.
4.3 Core components
A. Browser Developer Playground
Provides a browser-based interface for submitting prompts and viewing generated responses. It serves as an accessible testing environment for developers experimenting with the Workbench.
B. FastAPI Backend
Exposes HTTP endpoints to the browser interface, validates incoming requests, invokes the SDK, and returns generated text or a controlled error response.
C. Python SDK
Provides the developer-facing interface for calling N-ATLaS through a configured runtime. The SDK reduces the need for each application to implement its own runtime-selection and inference-connection logic.
D. Runtime Abstraction Layer
Defines a common interface for runtime implementations. This allows different inference backends to be used behind a consistent application-facing contract.
E. Gradio Runtime Adapter
Connects to a configured Gradio-hosted inference service using the Gradio client library.
F. OpenAI-Compatible Runtime Adapter
Uses the OpenAI Python client to communicate with an endpoint that implements the expected OpenAI-compatible chat-completions interface.
G. OpenAI-Compatible Gateway
A locally tested FastAPI service that accepts authenticated OpenAI-style requests and forwards inference requests to the configured Gradio service. This makes the hosted inference service accessible through a familiar API format for compatible clients.
H. Local GGUF Runtime
Uses llama-cpp-python to load and execute a compatible GGUF model locally. This component remains subject to successful model loading and inference validation.
5. Technology Stack
Technology	Role
Python	SDK, runtime adapters and backend implementation
FastAPI	HTTP backend and local gateway
Pydantic	Request and response validation
Gradio Client	Communication with the hosted Gradio inference service
OpenAI Python client	OpenAI-compatible endpoint integration
llama-cpp-python	Local GGUF inference integration
HTML and JavaScript	Browser playground interface
Pytest	Automated testing
FastAPI TestClient	HTTP endpoint testing
The implementation is designed to use Python-based components for the main integration logic while maintaining a lightweight browser interface for interactive testing.
6. Repository Organisation
The principal project areas include:
•	adapter/natlas/ — adapter and connection-related functionality.
•	runtime/ — runtime interfaces and backend-specific implementations.
•	sdk/natlas_sdk/ — the Python SDK.
•	playground/app.py — FastAPI backend for the developer playground.
•	playground/static/index.html — browser interface.
•	apps/ — application or gateway-related components, depending on the current checkout.
•	tests/ — automated tests.
•	docs/ — developer guides and technical documentation where available.
•	models/ — recommended local storage location for GGUF model files.
The exact files in a working checkout may differ as development progresses. Large model files should normally be stored outside Git version control rather than committed to the application repository.
7. Runtime Configuration
7.1 Hosted Gradio runtime
The Gradio runtime uses the following environment variable:
NATLAS_GRADIO_BASE_URL
A third-party community Hugging Face Space used during testing is:
https://koladeodunope-ednai-natlas-runtime.hf.space
Example PowerShell configuration:
$env:NATLAS_RUNTIME = "gradio"
$env:NATLAS_GRADIO_BASE_URL = "https://koladeodunope-ednai-natlas-runtime.hf.space"
This endpoint is a community-hosted service used for testing. It is not represented as an official NCAIR-hosted inference endpoint, and its continued availability is outside the Workbench's control.
7.2 OpenAI-compatible runtime
The OpenAI-compatible runtime uses the following environment variables:
•	NATLAS_RUNTIME
•	NATLAS_BASE_URL
•	NATLAS_API_KEY
•	NATLAS_MODEL
Example configuration for the locally tested gateway:
$env:NATLAS_RUNTIME = "openai"
$env:NATLAS_BASE_URL = "http://127.0.0.1:8001/v1"
$env:NATLAS_API_KEY = "your-local-development-key"
$env:NATLAS_MODEL = "N-ATLaS"
The gateway must be running separately on port 8001 for this configuration. The API key must match the key configured in the gateway.
The gateway supports a model-list endpoint and a non-streaming chat-completions endpoint. Token usage values returned by the current implementation are placeholders and must not be interpreted as actual token counts.
7.3 Local GGUF runtime
The local runtime is configured through:
•	NATLAS_RUNTIME=llama_cpp
•	NATLAS_MODEL_PATH
•	NATLAS_N_CTX
•	NATLAS_N_GPU_LAYERS
Example configuration, subject to the actual downloaded filename:
$env:NATLAS_RUNTIME = "llama_cpp"
$env:NATLAS_MODEL_PATH = "E:\N-ATLAS - Copy\developer-workbench\models\natlas\actual-model-file.gguf"
$env:NATLAS_N_CTX = "1024"
$env:NATLAS_N_GPU_LAYERS = "0"
The example uses CPU inference and a reduced context size to limit memory pressure on the development computer. The path must be replaced with the actual model file location.
The model repository selected for investigation is:
inuwamobarak/N-ATLaS-8B-GGUF-Q4_K_M
Model provenance, licensing, compatibility, and redistribution permissions should be checked before distributing the model with an application.
8. Installation and Execution
8.1 Development environment
The current development environment uses Windows 11, Python 3.13.5, and a Python virtual environment.
A typical setup from the repository root is:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
The installed dependencies should match the requirements and configuration for the specific runtime being used.
8.2 Starting the browser playground
After configuring a runtime, start the backend:
uvicorn playground.app:app --reload --port 8000
Open the following address in a browser:
http://127.0.0.1:8000
For the OpenAI-compatible route, start the gateway separately before using the playground. Environment variables configured in one PowerShell terminal are not automatically shared with another terminal process.
8.3 Local inference
Local inference requires a compatible GGUF model file in addition to the installed llama-cpp-python package. The runtime should not be considered fully operational until the model loads successfully and returns a generated response.
9. Verification and Testing
The following checks have been performed during development.
9.1 Python package verification
The llama-cpp-python installation was verified with:
python -c "from llama_cpp import Llama; print('llama-cpp-python installed successfully')"
The import succeeded. This verifies package availability but does not prove that a particular model file loads or generates text.
9.2 Gateway health check
The local gateway returned a healthy status indicating that the upstream endpoint and authentication configuration were present.
9.3 OpenAI-compatible API test
A request was sent to the gateway using the chat-completions format. The gateway returned HTTP 200 and generated text.
9.4 Browser playground integration test
The workbench was configured to use the OpenAI-compatible runtime and local gateway. A Yoruba translation prompt was submitted through the browser, and the playground successfully displayed a generated response.
This verifies the tested request path from the browser interface through the SDK and gateway to the hosted inference service.
9.5 Local GGUF verification status
The initial search of the project model directory and Downloads folder did not find a GGUF file. The model download and direct local-generation test remain outstanding.
The final submission should reflect the status of the actual repository and tests at the time it is submitted.
10. Developer Use Cases
The Workbench is intended to support application-development activities such as:
Prompt prototyping: Developers can try instructions and inspect model responses before incorporating prompts into application code.
Python application integration: Developers can use the SDK as a common entry point for inference requests.
Runtime experimentation: Developers can compare connection approaches and choose a runtime suited to their development or deployment environment.
Language-focused prototypes: Developers can experiment with tasks such as translation and text generation, including Yoruba prompts, subject to the model's actual capabilities.
Application integration development: The SDK and runtime abstraction provide a foundation for integrating model inference into web applications, utilities, and other software systems.
These are intended use cases. Their inclusion does not imply that every application type or language task has undergone formal evaluation.
11. Security and Operational Considerations
The current implementation is intended for development and experimentation, not unrestricted public production deployment.
Key considerations include:
1.	Credential protection: API keys should be held in environment variables or an appropriately excluded local configuration file. Real secrets must not be committed to Git or included in public screenshots.
2.	Gateway exposure: The tested gateway was bound to 127.0.0.1. Public deployment requires additional security review and configuration.
3.	Authentication: The gateway uses bearer-token authentication for its protected endpoints. Production use would require secure key management and an appropriate access-control strategy.
4.	Third-party dependency: The hosted Gradio service may change or become unavailable.
5.	Resource requirements: Local inference depends on RAM, CPU performance, model size, context settings, and the installed runtime build.
6.	Output quality: Successful inference demonstrates technical connectivity, not universal accuracy or suitability for high-stakes decisions.
7.	Reliability: Timeouts, upstream failures, request validation, and logging should be reviewed and tested before production deployment.
12. Current Limitations
The project remains in progress. The principal limitations are:
•	Local GGUF model loading and inference have not yet been verified.
•	The gateway currently supports non-streaming responses.
•	The current gateway's token usage values are placeholders.
•	The tested hosted inference endpoint is maintained by a third party.
•	The successful Yoruba prompt is a connectivity test, not a formal language-quality evaluation.
•	Production deployment, scalability, security hardening, and broader automated evaluation require further work.
The project should not be described as production-ready or as providing completed fine-tuning capabilities unless these are separately implemented and verified.
13. Future Development Roadmap
The next development stages are:
1.	Complete the GGUF download and test direct local inference.
2.	Improve the playground's runtime selection and configuration-status display.
3.	Expand developer quickstarts and copyable integration examples.
4.	Strengthen automated tests for runtime configuration and failure handling.
5.	Extend the SDK and application examples as requirements become clearer.
6.	Improve evaluation workflows with reproducible test prompts and documented metrics.
7.	Review authentication, secrets management, monitoring, and rate limiting before public deployment.
8.	Validate the installation process and documentation against a clean environment.
14. Conclusion
The N-ATLaS Developer Workbench is being developed as a reusable software integration toolkit for developers building applications with N-ATLaS.
Its core contribution is the separation of application code from inference-runtime configuration through a Python SDK and runtime abstraction, supported by a browser-based playground. The hosted Gradio and OpenAI-compatible inference routes have been verified during development, while local GGUF inference remains under configuration.
The project establishes a foundation for making N-ATLaS more accessible to application developers through practical integration tooling, documented workflows, and an extensible architecture.
Repository: https://github.com/emmybaba/natlas-developer-workbench
GGUF repository selected for local testing: https://huggingface.co/inuwamobarak/N-ATLaS-8B-GGUF-Q4_K_M
Hosted inference endpoint used during testing: https://koladeodunope-ednai-natlas-runtime.hf.space
________________________________________

