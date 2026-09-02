import { ChatApp } from "@/components/chat/ChatApp";
import { ThemeSync } from "@/components/ThemeSync";

export const metadata = { title: "Chat" };

export default function ChatPage() {
  return (
    <>
      <ThemeSync />
      <ChatApp />
    </>
  );
}
