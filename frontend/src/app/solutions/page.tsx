'use client';

import Link from 'next/link';
import { useSolutions } from '@/features/solutions/useSolutions';
import { Button } from '@/components/ui/button';

export default function SolutionsPage() {
  const { solutions, isLoading, error } = useSolutions();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error.message}</div>;
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Solutions</h1>
        <Button asChild>
          <Link href="/solutions/new">Create Solution</Link>
        </Button>
      </div>
      <ul>
        {solutions.map((solution) => (
          <li key={solution.solution_id}>
            <Link href={`/solutions/${solution.solution_id}`}>
              {solution.name}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}