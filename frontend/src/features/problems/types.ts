import { Project } from "../projects/types";
import { Solution } from "../solutions/types";
export interface Problem {
  problem_id: number;
  name: string;
  context: string | null;
  created_at: string | null;
  is_processed: boolean | null;
  project_id: number | null;
  project?: Project;
  solutions?: Solution[];
}
export type ProblemCreate = Omit<Problem, 'problem_id' | 'created_at' | 'is_processed' | 'project' | 'solutions'>;
export type ProblemUpdate = Partial<ProblemCreate>;