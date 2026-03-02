-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS public.users (
    user_id BIGINT NOT NULL,
    username TEXT,
    first_name TEXT,
    response_style TEXT NOT NULL DEFAULT 'normal',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT users_pkey PRIMARY KEY (user_id)
);

-- Chats table
CREATE TABLE IF NOT EXISTS public.chats (
    chat_id BIGINT NOT NULL,
    type TEXT NOT NULL,
    response_style TEXT NOT NULL DEFAULT 'normal',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT chats_pkey PRIMARY KEY (chat_id)
);

-- Messages history table
CREATE TABLE IF NOT EXISTS public.messages_history (
    message_id BIGSERIAL NOT NULL,
    chat_id BIGINT NOT NULL,
    user_id BIGINT,
    tg_message_id BIGINT,
    date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    message_text TEXT NOT NULL,
    reply_text TEXT,
    pipeline_used TEXT,
    CONSTRAINT messages_history_pkey PRIMARY KEY (message_id)
);

-- Organizations table
CREATE TABLE IF NOT EXISTS public.organizations (
    organization_id SERIAL NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    website CHARACTER VARYING,
    contact_email CHARACTER VARYING,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT organizations_pkey PRIMARY KEY (organization_id)
);

-- Organizations vector table
CREATE TABLE IF NOT EXISTS public.organizations_vec (
    organization_id INTEGER NOT NULL,
    text_to_embed TEXT NOT NULL,
    embedding vector(1536),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT organizations_vec_pkey PRIMARY KEY (organization_id),
    CONSTRAINT organizations_vec_organization_id_fkey FOREIGN KEY (organization_id)
        REFERENCES public.organizations(organization_id)
);

-- Solutions table
CREATE TABLE IF NOT EXISTS public.solutions (
    solution_id BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    name TEXT NOT NULL,
    context TEXT,
    content TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    embedding vector(1536),
    CONSTRAINT solutions_pkey PRIMARY KEY (solution_id)
);

-- Solutions vector table
CREATE TABLE IF NOT EXISTS public.solutions_vec (
    solution_id BIGINT NOT NULL,
    text_to_embed TEXT NOT NULL,
    embedding vector(1536),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT solutions_vec_pkey PRIMARY KEY (solution_id),
    CONSTRAINT solutions_vec_solution_id_fkey FOREIGN KEY (solution_id)
        REFERENCES public.solutions(solution_id)
);

-- Problems table
CREATE TABLE IF NOT EXISTS public.problems (
    problem_id BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    name TEXT NOT NULL,
    context TEXT,
    content TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    is_processed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    embedding vector(1536),
    CONSTRAINT problems_pkey PRIMARY KEY (problem_id)
);

-- Problems vector table
CREATE TABLE IF NOT EXISTS public.problems_vec (
    problem_id BIGINT NOT NULL,
    text_to_embed TEXT NOT NULL,
    embedding vector(1536),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT problems_vec_pkey PRIMARY KEY (problem_id),
    CONSTRAINT problems_vec_problem_id_fkey FOREIGN KEY (problem_id)
        REFERENCES public.problems(problem_id)
);

-- Projects table
CREATE TABLE IF NOT EXISTS public.projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    organization_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    embedding vector(1536),
    CONSTRAINT projects_pkey PRIMARY KEY (project_id),
    CONSTRAINT projects_organization_id_fkey FOREIGN KEY (organization_id)
        REFERENCES public.organizations(organization_id)
);

-- Projects vector table
CREATE TABLE IF NOT EXISTS public.projects_vec (
    project_id BIGINT NOT NULL,
    text_to_embed TEXT NOT NULL,
    embedding vector(1536),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT projects_vec_pkey PRIMARY KEY (project_id),
    CONSTRAINT projects_vec_project_id_fkey FOREIGN KEY (project_id)
        REFERENCES public.projects(project_id)
);

-- Problems <-> Solutions mapping
CREATE TABLE IF NOT EXISTS public.problems_solutions (
    problem_id BIGINT NOT NULL,
    solution_id BIGINT NOT NULL,
    similarity_score DOUBLE PRECISION NOT NULL,
    matched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT problems_solutions_pkey PRIMARY KEY (problem_id, solution_id),
    CONSTRAINT fk_prs_problem FOREIGN KEY (problem_id) REFERENCES public.problems(problem_id),
    CONSTRAINT fk_prs_solution FOREIGN KEY (solution_id) REFERENCES public.solutions(solution_id)
);

-- Projects <-> Solutions mapping
CREATE TABLE IF NOT EXISTS public.projects_solutions (
    project_id BIGINT NOT NULL,
    solution_id BIGINT NOT NULL,
    similarity_score DOUBLE PRECISION NOT NULL,
    matched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT projects_solutions_pkey PRIMARY KEY (project_id, solution_id),
    CONSTRAINT fk_ps_project FOREIGN KEY (project_id) REFERENCES public.projects(project_id),
    CONSTRAINT fk_ps_solution FOREIGN KEY (solution_id) REFERENCES public.solutions(solution_id)
);

-- Organizations <-> Solutions mapping
CREATE TABLE IF NOT EXISTS public.organizations_solutions (
    organization_id INTEGER NOT NULL,
    solution_id BIGINT NOT NULL,
    similarity_score DOUBLE PRECISION NOT NULL,
    matched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT organizations_solutions_pkey PRIMARY KEY (organization_id, solution_id),
    CONSTRAINT organizations_solutions_organization_id_fkey FOREIGN KEY (organization_id)
        REFERENCES public.organizations(organization_id),
    CONSTRAINT organizations_solutions_solution_id_fkey FOREIGN KEY (solution_id)
        REFERENCES public.solutions(solution_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON public.messages_history(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON public.messages_history(user_id);
CREATE INDEX IF NOT EXISTS idx_problems_processed ON public.problems(is_processed);
