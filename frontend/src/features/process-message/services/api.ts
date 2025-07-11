import { getAuthHeaders } from '@/services/api';
import { Response } from '../../messages/types'; // Import the unified Response type from messages feature

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const processMessage = async ({ message }: { message: string }): Promise<Response> => { // Use Response type
    const response = await fetch(`${API_URL}/process-message`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders()
        },
        body: JSON.stringify({ message }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to process message');
    }

    return response.json();
};