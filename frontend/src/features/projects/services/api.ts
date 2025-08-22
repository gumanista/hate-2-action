import { getAuthHeaders } from '@/services/api';
import { Project, ProjectCreate, ProjectUpdate } from '../types/index';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const getProjects = async (): Promise<Project[]> => {
    const response = await fetch(`${API_URL}/projects`, { headers: getAuthHeaders() });
    if (!response.ok) {
        const text = await response.text();
        console.error('[getProjects] failed:', response.status, response.statusText, text);
        throw new Error(`Failed to fetch projects: ${response.status} ${response.statusText}`);
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
  const headers = {
    ...getAuthHeaders(),
    'Content-Type': 'application/json',
  };

  const response = await fetch(`${API_URL}/projects`, {
    method: 'POST',
    headers,
    body: JSON.stringify(project),
  });

  if (!response.ok) {
    const text = await response.text();
    console.error('[createProject] failed:', response.status, response.statusText, text);
    throw new Error(`Failed to create project: ${response.status} ${response.statusText}`);
  }

  return response.json();
};

export const updateProject = async (id: number, project: ProjectUpdate): Promise<Project> => {
  const headers = {
    ...getAuthHeaders(),
    'Content-Type': 'application/json',
  };

  const response = await fetch(`${API_URL}/projects/${id}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(project),
  });

  if (!response.ok) {
    const text = await response.text();
    console.error('[updateProject] failed:', response.status, response.statusText, text);
    throw new Error(`Failed to update project: ${response.status} ${response.statusText}`);
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