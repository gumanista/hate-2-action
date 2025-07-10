import { Organization } from './types';
import { fetcher } from '../../lib/api';

export const getOrganizations = async (): Promise<Organization[]> => {
  return fetcher('/organizations');
};

export const getOrganization = async (id: number): Promise<Organization> => {
  return fetcher(`/organizations/${id}`);
};