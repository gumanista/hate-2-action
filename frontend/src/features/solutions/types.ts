import { Problem } from "../problems/types";
export interface Solution {
  solution_id: number;
  name: string;
  context: string | null;
  created_at: string | null;
  problem_id: number | null;
  problem?: Problem;
}