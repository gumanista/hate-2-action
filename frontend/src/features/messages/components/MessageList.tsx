"use client";

import { useEffect, useState } from "react";
import Link from "next/link"; // Import Link
import { getMessages } from "../services/api";
import { Message } from "../types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function MessageList() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const data = await getMessages();
        setMessages(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An unknown error occurred");
      } finally {
        setIsLoading(false);
      }
    };

    fetchMessages();
  }, []);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <Link href={`/messages/${message.message_id}`} key={message.message_id}>
          <Card className="cursor-pointer hover:bg-gray-100">
            <CardHeader>
              <CardTitle>{message.chat_title || "Direct Message"}</CardTitle>
            </CardHeader>
            <CardContent>
              <p><strong>From:</strong> @{message.user_username}</p>
              <p>{message.text}</p>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}