"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { processMessage } from "../services/api";

import { ProcessMessageResponse } from "../types";

export function ProcessMessageForm() {
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ProcessMessageResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setResult(null);

    try {
      const data = await processMessage({ message });
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
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Textarea
          placeholder="Enter your message here"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={6}
        />
        <Button type="submit" disabled={isLoading}>
          {isLoading ? "Processing..." : "Process Message"}
        </Button>
      </form>
      {result && (
        <div>
          <h3 className="text-lg font-semibold">Reply:</h3>
          <p>{result.reply_text}</p>

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
        </div>
      )}
    </div>
  );
}