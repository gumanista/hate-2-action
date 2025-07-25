"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { processMessage } from "../services/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Response } from "../../messages/types"; // Import the unified Response type

export function ProcessMessageForm() {
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<Response | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [responseStyle, setResponseStyle] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setResult(null);

    try {
      const data = await processMessage({ message, response_style: responseStyle });
      setResult(data);
      toast.success("Message processed successfully.");
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <Card className="border-gray-200 shadow-sm">
        <CardHeader>
          <CardTitle>Process Message</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Textarea
              placeholder="Type here..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={6}
              className="focus:caret-blue-500"
            />
            <div>
              <label htmlFor="response-style" className="block text-sm font-medium text-gray-700 mb-2">
                Response Style
              </label>
              <select
                id="response-style"
                value={responseStyle}
                onChange={(e) => setResponseStyle(e.target.value)}
                className="border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:bg-input/30 flex field-sizing-content h-10 w-1/2 rounded-md border bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[1px] disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
              >
                <option value="" disabled>
                  Select a style
                </option>
                <option value="empathetic">Empathetic</option>
                <option value="rude">Rude</option>
                <option value="formal">Formal</option>
              </select>
            </div>
            <Button type="submit" disabled={isLoading || !responseStyle}>
              {isLoading ? "Processing..." : "Process Message"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {isLoading ? (
        <Card className="animate-pulse border-gray-200 shadow-sm">
          <CardContent className="p-6">
            <div className="h-4 bg-gray-200 rounded mb-2 w-3/4" />
            <div className="h-4 bg-gray-200 rounded w-full" />
          </CardContent>
        </Card>
      ) : result ? (
        <Card className="border-gray-200 shadow-sm">
          <CardHeader>
            <CardTitle>Response</CardTitle>
          </CardHeader>
          <CardContent>
            <h3 className="text-lg font-semibold">Reply:</h3>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.text}</ReactMarkdown>

            <h3 className="text-lg font-semibold mt-4">Recommended Problems:</h3>
            <ul>
              {result.problems.map((problem) => (
                <li key={problem.problem_id}>
                  <a href={`/problems/${problem.problem_id}`} className="text-blue-500 hover:underline">
                    {problem.name}
                  </a>
                </li>
              ))}
            </ul>

            <h3 className="text-lg font-semibold mt-4">Recommended Solutions:</h3>
            <ul>
              {result.solutions.map((solution) => (
                <li key={solution.solution_id}>
                  <a href={`/solutions/${solution.solution_id}`} className="text-blue-500 hover:underline">
                    {solution.name}
                  </a>
                </li>
              ))}
            </ul>

            <h3 className="text-lg font-semibold mt-4">Recommended Projects:</h3>
            <ul>
              {result.projects.map((project) => (
                <li key={project.project_id}>
                  <a href={`/projects/${project.project_id}`} className="text-blue-500 hover:underline">
                    {project.name}
                  </a>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}