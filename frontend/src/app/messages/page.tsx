import { MessageList } from "@/features/messages/components/MessageList";

export default function MessagesPage() {
  return (
    <main className="container mx-auto py-8">
      <h1 className="text-2xl font-bold mb-4">Messages</h1>
      <MessageList />
    </main>
  );
}