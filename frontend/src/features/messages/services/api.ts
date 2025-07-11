import { getAuthHeaders } from '@/services/api';
import { Message } from '../types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const getMessages = async (): Promise<Message[]> => {
    const response = await fetch(`${API_URL}/messages`, { headers: getAuthHeaders() });
    if (!response.ok) {
        throw new Error('Failed to fetch messages');
    }
    return response.json();
};

export const getMessageById = async (id: string): Promise<Message> => {
    const response = await fetch(`${API_URL}/messages/${id}`, { headers: getAuthHeaders() });
    if (!response.ok) {
        throw new Error(`Failed to fetch message with ID ${id}`);
    }
    return response.json();
};