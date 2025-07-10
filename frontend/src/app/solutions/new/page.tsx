'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { SolutionForm } from '@/features/solutions/components/SolutionForm';
import { createSolution } from '@/features/solutions/services/api';
import { SolutionCreate, SolutionUpdate } from '@/features/solutions/types/index';

export default function NewSolutionPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (values: SolutionCreate | SolutionUpdate) => {
    setIsSubmitting(true);
    try {
      await createSolution(values as SolutionCreate);
      router.push('/solutions');
    } catch (error) {
      console.error(error);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container mx-auto py-10">
      <h1 className="text-2xl font-bold mb-4">New Solution</h1>
      <SolutionForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
    </div>
  );
}