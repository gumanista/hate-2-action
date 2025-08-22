import { Organization } from './types';
import { Project } from '../projects/types';
import { fetcher } from '../../lib/api';

export const getOrganizations = async (): Promise<Organization[]> => {
  return fetcher('/organizations');
};

export const getOrganization = async (id: number): Promise<Organization> => {
  return fetcher(`/organizations/${id}`);
};
export const getProjectsByOrganization = async (organization_id: number): Promise<Project[]> => {
  return fetcher(`/organizations/${organization_id}/projects`);
};