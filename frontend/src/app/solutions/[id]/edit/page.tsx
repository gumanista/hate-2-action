'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getSolution, updateSolution } from '@/features/solutions/services/api';
import { Solution, SolutionUpdate } from '@/features/solutions/types/index';
import { SolutionForm } from '@/features/solutions/components/SolutionForm';

export default function EditSolutionPage() {
  const params = useParams();
  const router = useRouter();
  const [solution, setSolution] = useState<Solution | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
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

  const handleSubmit = async (values: SolutionUpdate) => {
    setIsSubmitting(true);
    if (id) {
      try {
        await updateSolution(id, values);
        router.push(`/solutions/${id}`);
      } catch (error) {
        console.error(error);
        setIsSubmitting(false);
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
      <h1 className="text-2xl font-bold mb-4">Edit Solution</h1>
      <SolutionForm
        solution={solution}
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}