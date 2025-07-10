import { useState, useEffect } from 'react';
import { Problem } from '@/types';
import { getProblems } from '@/services/problems';

export const useProblems = () => {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchProblems = async () => {
      try {
        const data = await getProblems();
        setProblems(data);
      } catch (err) {
        setError(err as Error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProblems();
  }, []);

  return { problems, isLoading, error };
};