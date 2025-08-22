import { Organization, OrganizationCreate, OrganizationUpdate } from '../types';
import { api } from '@/lib/api';

export const getOrganizations = async (): Promise<Organization[]> => {
  const response = await api.get('/organizations');
  return response.data;
};

export const getOrganization = async (id: number): Promise<Organization> => {
    const response = await api.get(`/organizations/${id}`);
    return response.data;
};

export const createOrganization = async (organization: OrganizationCreate): Promise<Organization> => {
    const response = await api.post('/organizations', organization);
    return response.data;
};

export const updateOrganization = async (id: number, organization: OrganizationUpdate): Promise<Organization> => {
    const response = await api.put(`/organizations/${id}`, organization);
    return response.data;
};

export const deleteOrganization = async (id: number): Promise<void> => {
    await api.delete(`/organizations/${id}`);
};