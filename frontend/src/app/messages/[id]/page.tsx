"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getMessageById } from "@/features/messages/services/api";
import { Message } from "@/features/messages/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MessageDetailPage() {
  const { id } = useParams();
  const [message, setMessage] = useState<Message | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      const fetchMessage = async () => {
        try {
          const data = await getMessageById(id as string);
          setMessage(data);
        } catch (err) {
          setError(err instanceof Error ? err.message : "An unknown error occurred");
        } finally {
          setIsLoading(false);
        }
      };
      fetchMessage();
    }
  }, [id]);

  if (isLoading) {
    return <div className="container mx-auto py-8">Loading...</div>;
  }

  if (error) {
    return <div className="container mx-auto py-8">Error: {error}</div>;
  }

  if (!message) {
    return <div className="container mx-auto py-8">Message not found.</div>;
  }

  return (
    <main className="container mx-auto py-8">
      <h1 className="text-2xl font-bold mb-4">Message Details</h1>
      <Card>
        <CardHeader>
          <CardTitle>{message.chat_title || "Direct Message"}</CardTitle>
        </CardHeader>
        <CardContent>
          <p><strong>From:</strong> @{message.user_username}</p>
          <p><strong>Message:</strong> {message.text}</p>

          {message.response && (
            <div className="mt-4">
              <h3 className="text-lg font-semibold">Reply:</h3>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.response.text}</ReactMarkdown>

              {message.response.problems && message.response.problems.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-lg font-semibold">Recommended Problems:</h3>
                  <ul>
                    {message.response.problems.map((problem) => (
                      <li key={problem.problem_id}>
                        <a href={`/problems/${problem.problem_id}`} className="text-blue-500 hover:underline">
                          {problem.name}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {message.response.solutions && message.response.solutions.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-lg font-semibold">Recommended Solutions:</h3>
                  <ul>
                    {message.response.solutions.map((solution) => (
                      <li key={solution.solution_id}>
                        <a href={`/solutions/${solution.solution_id}`} className="text-blue-500 hover:underline">
                          {solution.name}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {message.response.projects && message.response.projects.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-lg font-semibold">Recommended Projects:</h3>
                  <ul>
                    {message.response.projects.map((project) => (
                      <li key={project.project_id}>
                        <a href={`/projects/${project.project_id}`} className="text-blue-500 hover:underline">
                          {project.name}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}