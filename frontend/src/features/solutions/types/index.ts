export interface Solution {
    solution_id: number;
    name: string;
    context: string | null;
    created_at: string | null;
}

export interface SolutionCreate {
    name: string;
    context: string;
}

export interface SolutionUpdate {
    name?: string;
    context?: string;
}