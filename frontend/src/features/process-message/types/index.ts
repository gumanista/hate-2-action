export interface ProcessMessageRequest {
  message: string;
}

export interface Problem {
  problem_id: number;
  name: string;
  context: string | null;
}

export interface Solution {
  solution_id: number;
  name: string;
  context: string | null;
}

export interface Project {
  project_id: number;
  name: string;
  description: string | null;
}

export interface ProcessMessageResponse {
  reply_text: string;
  problems: Problem[];
  solutions: Solution[];
  projects: Project[];
}