// {{project_name}}: call N-ATLaS through the workbench's OpenAI-compatible gateway.
// Requires Node.js 18+. No dependencies.
//
//   node chat.mjs "Translate into Yoruba: Good morning"
//   node chat.mjs --system "Answer in one sentence." "What is antimicrobial resistance?"

const BASE_URL = process.env.NATLAS_BASE_URL ?? "http://127.0.0.1:8000/v1";
const API_KEY = process.env.NATLAS_API_KEY; // only needed if the gateway sets NATLAS_GATEWAY_KEY
const MODEL = process.env.NATLAS_MODEL ?? "natlas";

const args = process.argv.slice(2);
let system;

if (args[0] === "--system") {
  system = args[1];
  args.splice(0, 2);
}

const prompt = args.join(" ").trim();

if (!prompt) {
  console.error('Usage: node chat.mjs [--system "..."] "your prompt"');
  process.exit(2);
}

export async function chat(messages) {
  const response = await fetch(`${BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {}),
    },
    body: JSON.stringify({ model: MODEL, messages }),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body.error?.message ?? `Request failed (HTTP ${response.status})`);
  }

  return body.choices[0].message.content;
}

try {
  const messages = [];
  if (system) messages.push({ role: "system", content: system });
  messages.push({ role: "user", content: prompt });
  console.log(await chat(messages));
} catch (error) {
  console.error("error:", error.message);
  process.exit(1);
}
