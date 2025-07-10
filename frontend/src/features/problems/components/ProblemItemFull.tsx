import React from 'react';
import { Problem } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SolutionList } from '@/features/solutions/components/SolutionList';

interface ProblemItemFullProps {
  problem: Problem;
}

export const ProblemItemFull: React.FC<ProblemItemFullProps> = ({ problem }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{problem.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{problem.context}</p>
        <Badge>{problem.is_processed ? 'Processed' : 'Not Processed'}</Badge>
        <div className="mt-4">
          <h3 className="text-lg font-semibold">Solutions</h3>
          {problem.solutions && problem.solutions.length > 0 ? (
            <SolutionList solutions={problem.solutions} />
          ) : (
            <p>No solutions for this problem yet.</p>
          )}
        </div>
        <div className="mt-4">
          <h3 className="text-lg font-semibold">Project ID</h3>
          <p>{problem.project_id}</p>
        </div>
      </CardContent>
    </Card>
  );
};