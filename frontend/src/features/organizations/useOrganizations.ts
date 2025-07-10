import { useState, useEffect } from 'react';
import { getOrganizations } from './services';
import { Organization } from './types';

export function useOrganizations() {
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        const fetchOrganizations = async () => {
            try {
                const data = await getOrganizations();
                setOrganizations(data);
            } catch (err) {
                setError(err as Error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchOrganizations();
    }, []);

    return { organizations, isLoading, error };
}