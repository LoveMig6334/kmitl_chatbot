import { streamChat, aiConfigured } from "@/lib/ai";

export async function POST(req: Request) {
  const { messages, facultyScope } = await req.json();
  const turns = (messages ?? [])
    .filter((m: { role: string; content: string }) => 
      (m.role === "user" || m.role === "assistant") && typeof m.content === "string",
    )
    .map((m: { role: string; content: string }) => ({
      role: m.role,
      content: m.content,
    }));

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      try {
        for await (const chunk of streamChat(turns, facultyScope ?? [])) {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ delta: chunk })}\n\n`),
          );
        }
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ done: true })}\n\n`));
      } catch (err) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ error: String(err) })}\n\n`),
        );
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-AI-Configured": aiConfigured ? "1" : "0",
    },
  });
}
