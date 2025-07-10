import { Project } from "../../projects/types";
export interface Organization {
    id: number;
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
}

export interface OrganizationUpdate {
    name?: string;
    description?: string;
}