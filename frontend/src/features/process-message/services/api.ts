import { getAuthHeaders } from '@/services/api';
import { ProcessMessageRequest, ProcessMessageResponse } from '../types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const processMessage = async (data: ProcessMessageRequest): Promise<ProcessMessageResponse> => {
    const response = await fetch(`${API_URL}/process-message`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        throw new Error('Failed to process message');
    }
    return response.json();
};