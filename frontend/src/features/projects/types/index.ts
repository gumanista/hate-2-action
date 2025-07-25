export interface Project {
    project_id: number;
    name: string;
    description: string | null;
    created_at: string | null;
    organization_id: number | null;
    website: string | null;
    contact_email: string | null;
}

export interface ProjectCreate {
    name: string;
    description: string;
    organization_id: number | null;
    website: string | null;
    contact_email: string | null;
}

export interface ProjectUpdate {
    name?: string;
    description?: string;
    organization_id?: number | null;
}