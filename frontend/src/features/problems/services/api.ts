import { getAuthHeaders } from '@/services/api';
import { Problem } from '@/features/problems/types';
import { ProblemCreate, ProblemUpdate } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const getProblems = async (): Promise<Problem[]> => {
    const response = await fetch(`${API_URL}/problems`, { headers: getAuthHeaders() });
    if (!response.ok) {
        throw new Error('Failed to fetch problems');
    }
    return response.json();
};

export const getProblem = async (id: number): Promise<Problem> => {
    const response = await fetch(`${API_URL}/problems/${id}`, { headers: getAuthHeaders() });
    if (!response.ok) {
        throw new Error('Failed to fetch problem');
    }
    return response.json();
};

export const createProblem = async (problem: ProblemCreate): Promise<Problem> => {
    const response = await fetch(`${API_URL}/problems`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(problem),
    });
    if (!response.ok) {
        throw new Error('Failed to create problem');
    }
    return response.json();
};

export const updateProblem = async (id: number, problem: ProblemUpdate): Promise<Problem> => {
    const response = await fetch(`${API_URL}/problems/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(problem),
    });
    if (!response.ok) {
        throw new Error('Failed to update problem');
    }
    return response.json();
};

export const deleteProblem = async (id: number): Promise<void> => {
    const response = await fetch(`${API_URL}/problems/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    if (!response.ok) {
        throw new Error('Failed to delete problem');
    }
};