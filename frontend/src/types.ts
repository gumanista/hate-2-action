export interface Problem {
    problem_id: number;
    name: string;
    context: string | null;
    created_at: string | null;
    is_processed: boolean | null;
}

export interface ProblemCreate {
    name: string;
    context: string | null;
}

export interface ProblemUpdate {
    name?: string;
    context?: string | null;
    is_processed?: boolean;
}