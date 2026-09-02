export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export const aiConfigured = Boolean(process.env.AI_BASE_URL && process.env.AI_API_KEY);

const baseUrl = process.env.AI_BASE_URL;
const apiKey = process.env.AI_API_KEY;
const model = process.env.AI_MODEL || "gpt-4o-mini";

function buildSystemPrompt(facultyScope: string[]) {
  let system =
    "You are a friendly university study assistant. Answer concisely in the language the user writes in.";
  if (facultyScope.length > 0) {
    system += ` The conversation is scoped to these faculties: ${facultyScope.join(", ")}.`;
  }
  return system;
}

export async function* streamChat(
  turns: ChatTurn[],
  facultyScope: string[],
): AsyncGenerator<string> {
  if (!aiConfigured || !baseUrl || !apiKey) {
    yield* mockStream(turns);
    return;
  }

  const system = buildSystemPrompt(facultyScope);
  const res = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      stream: true,
      messages: [{ role: "system", content: system }, ...turns],
    }),
  });

  if (!res.ok || !res.body) {
    yield `Sorry, the AI provider returned an error (${res.status}). Check AI_BASE_URL and AI_API_KEY.`;
    return;
  }

  // Parse OpenAI-style SSE stream
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const data = trimmed.slice(5).trim();
      if (data === "[DONE]") return;
      try {
        const json = JSON.parse(data);
        const delta = json.choices?.[0]?.delta?.content;
        if (delta) yield delta;
      } catch {
        // ignore malformed lines
      }
    }
  }
}

async function* mockStream(turns: ChatTurn[]): AsyncGenerator<string> {
  const lastUser = [...turns].reverse().find((t) => t.role === "user");
  const full = lastUser ? lastUser.content : "Hello!";
  const reply = `You said: "${full}". This is a demo response. Connect an AI provider in .env (AI_BASE_URL + AI_API_KEY) to get real answers.`;
  for (const chunk of splitIntoChunks(reply)) {
    await sleep(24);
    yield chunk;
  }
}

function splitIntoChunks(text: string): string[] {
  const words = text.split(/(\s+)/);
  const chunks: string[] = [];
  for (const w of words) {
    if (w.length > 24) {
      for (let i = 0; i < w.length; i += 24) chunks.push(w.slice(i, i + 24));
    } else {
      chunks.push(w);
    }
  }
  return chunks;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
