import { getAuthHeaders } from '@/services/api';
import { Project, ProjectCreate, ProjectUpdate } from '../types/index';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const getProjects = async (): Promise<Project[]> => {
    const response = await fetch(`${API_URL}/projects`, { headers: getAuthHeaders() });
    if (!response.ok) {
        throw new Error('Failed to fetch projects');
    }
    return response.json();
};

export const getProject = async (id: number): Promise<Project> => {
    const response = await fetch(`${API_URL}/projects/${id}`, { headers: getAuthHeaders() });
    if (!response.ok) {
        throw new Error('Failed to fetch project');
    }
    return response.json();
};

export const createProject = async (project: ProjectCreate): Promise<Project> => {
    const response = await fetch(`${API_URL}/projects`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(project),
    });
    if (!response.ok) {
        throw new Error('Failed to create project');
    }
    return response.json();
};

export const updateProject = async (id: number, project: ProjectUpdate): Promise<Project> => {
    const response = await fetch(`${API_URL}/projects/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(project),
    });
    if (!response.ok) {
        throw new Error('Failed to update project');
    }
    return response.json();
};

export const deleteProject = async (id: number): Promise<void> => {
    const response = await fetch(`${API_URL}/projects/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    if (!response.ok) {
        throw new Error('Failed to delete project');
    }
};