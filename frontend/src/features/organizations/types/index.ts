import { Project } from "../../projects/types";
export interface Organization {
    organization_id: number;
    name: string;
    description: string | null;
    created_at: string | null;
    website: string | null;
    contact_email: string | null;
    projects?: Project[];
}

export interface OrganizationCreate {
    name: string;
    description: string;
    website?: string;
    contact_email?: string;
    project_ids?: number[];
}

export interface OrganizationUpdate {
    name?: string;
    description?: string;
    website?: string;
    project_ids?: number[];
}