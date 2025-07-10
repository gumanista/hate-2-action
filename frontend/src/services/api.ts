export const getAuthHeaders = (): Record<string, string> => {
    const apiKey = process.env.NEXT_PUBLIC_API_KEY;
    if (!apiKey) {
        console.error('API key is not defined. Please check your .env.local file.');
        return { 'Content-Type': 'application/json' };
    }
    return {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
    };
};