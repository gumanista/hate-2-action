import { getAuthHeaders } from '@/services/api';
import { Solution, SolutionCreate, SolutionUpdate } from '../types/index';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const getSolutions = async (): Promise<Solution[]> => {
    const response = await fetch(`${API_URL}/solutions`, { headers: getAuthHeaders() });
    if (!response.ok) {
        throw new Error('Failed to fetch solutions');
    }
    return response.json();
};

export const getSolution = async (id: number): Promise<Solution> => {
    const response = await fetch(`${API_URL}/solutions/${id}`, { headers: getAuthHeaders() });
    if (!response.ok) {
        throw new Error('Failed to fetch solution');
    }
    return response.json();
};

export const createSolution = async (solution: SolutionCreate): Promise<Solution> => {
    const response = await fetch(`${API_URL}/solutions`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(solution),
    });
    if (!response.ok) {
        throw new Error('Failed to create solution');
    }
    return response.json();
};

export const updateSolution = async (id: number, solution: SolutionUpdate): Promise<Solution> => {
    const response = await fetch(`${API_URL}/solutions/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(solution),
    });
    if (!response.ok) {
        throw new Error('Failed to update solution');
    }
    return response.json();
};

export const deleteSolution = async (id: number): Promise<void> => {
    const response = await fetch(`${API_URL}/solutions/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    if (!response.ok) {
        throw new Error('Failed to delete solution');
    }
};