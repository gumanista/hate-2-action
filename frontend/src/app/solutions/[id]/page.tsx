'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getSolution, deleteSolution } from '@/features/solutions/services/api';
import { Solution } from '@/features/solutions/types/index';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function SolutionPage() {
  const params = useParams();
  const router = useRouter();
  const [solution, setSolution] = useState<Solution | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const id = Number(params.id);

  useEffect(() => {
    if (id) {
      const fetchSolution = async () => {
        try {
          const data = await getSolution(id);
          setSolution(data);
        } catch (err) {
          setError(err as Error);
        } finally {
          setIsLoading(false);
        }
      };
      fetchSolution();
    }
  }, [id]);

  const handleDelete = async () => {
    if (id) {
      try {
        await deleteSolution(id);
        router.push('/solutions');
      } catch (err) {
        setError(err as Error);
      }
    }
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error.message}</div>;
  }

  if (!solution) {
    return <div>Solution not found</div>;
  }

  return (
    <div className="container mx-auto py-10">
      <h1 className="text-2xl font-bold mb-4">{solution.name}</h1>
      <p className="mb-4">{solution.context}</p>
      <div className="flex gap-4">
        <Button asChild>
          <Link href={`/solutions/${solution.solution_id}/edit`}>Edit</Link>
        </Button>
        <Button variant="destructive" onClick={handleDelete}>
          Delete
        </Button>
      </div>
    </div>
  );
}