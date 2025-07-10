import { useState, useEffect } from 'react';
import { getSolutions } from './services';
import { Solution } from './types';

export function useSolutions() {
    const [solutions, setSolutions] = useState<Solution[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        const fetchSolutions = async () => {
            try {
                const data = await getSolutions();
                setSolutions(data);
            } catch (err) {
                setError(err as Error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchSolutions();
    }, []);

    return { solutions, isLoading, error };
}