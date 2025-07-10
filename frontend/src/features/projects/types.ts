import { Organization } from "../organizations/types";
import { Problem } from "../problems/types";
export interface Project {
  project_id: number;
  name: string;
  description: string | null;
  created_at: string | null;
  website: string | null;
  contact_email: string | null;
  organization_id: number | null;
  organization?: Organization;
  problems?: Problem[];
}