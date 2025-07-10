import { getAuthHeaders } from '@/services/api';
import { Organization, OrganizationCreate, OrganizationUpdate } from '../types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const getOrganizations = async (): Promise<Organization[]> => {
    const response = await fetch(`${API_URL}/organizations`, { headers: getAuthHeaders() });
    if (!response.ok) {
        throw new Error('Failed to fetch organizations');
    }
    return response.json();
};

export const getOrganization = async (id: number): Promise<Organization> => {
    const response = await fetch(`${API_URL}/organizations/${id}`, { headers: getAuthHeaders() });
    if (!response.ok) {
        throw new Error('Failed to fetch organization');
    }
    return response.json();
};

export const createOrganization = async (organization: OrganizationCreate): Promise<Organization> => {
    const response = await fetch(`${API_URL}/organizations`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(organization),
    });
    if (!response.ok) {
        throw new Error('Failed to create organization');
    }
    return response.json();
};

export const updateOrganization = async (id: number, organization: OrganizationUpdate): Promise<Organization> => {
    const response = await fetch(`${API_URL}/organizations/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(organization),
    });
    if (!response.ok) {
        throw new Error('Failed to update organization');
    }
    return response.json();
};

export const deleteOrganization = async (id: number): Promise<void> => {
    const response = await fetch(`${API_URL}/organizations/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    if (!response.ok) {
        throw new Error('Failed to delete organization');
    }
};