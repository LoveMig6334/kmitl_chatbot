import { ChatApp } from "@/components/chat/ChatApp";
import { pageMetadata } from "@/i18n/server";

export const generateMetadata = () => pageMetadata("chat.pageTitle");

/** `/chat` (new chat) and `/chat/<id>` render the same component, so switching chats never remounts it. */
export default async function ChatPage({ params }: { params: Promise<{ chatId?: string[] }> }) {
  const { chatId } = await params;
  return <ChatApp chatId={chatId?.[0] ?? null} />;
}
