import { Problem } from "@/features/problems/types";
import { Solution } from "@/features/solutions/types";
import { Project } from "@/features/projects/types";

export interface Response {
  response_id?: number; // Optional for initial creation
  message_id?: number; // Optional for initial creation
  text: string;
  created_at?: string;
  problems: Problem[];
  solutions: Solution[];
  projects: Project[];
}

export interface Message {
  message_id: number;
  user_id: number;
  user_username: string;
  chat_title: string | null;
  text: string;
  response?: Response; // Optional response field
}