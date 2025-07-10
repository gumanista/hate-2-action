import React from 'react';
import { Solution } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface SolutionItemFullProps {
  solution: Solution;
}

export const SolutionItemFull: React.FC<SolutionItemFullProps> = ({ solution }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{solution.name}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div>
          <strong>ID:</strong> {solution.solution_id}
        </div>
        <div>
          <strong>Context:</strong> {solution.context}
        </div>
        <div>
          <strong>Created At:</strong> {solution.created_at}
        </div>
        {solution.problem_id && (
          <div>
            <strong>Problem ID:</strong> <Badge>{solution.problem_id}</Badge>
          </div>
        )}
      </CardContent>
    </Card>
  );
};