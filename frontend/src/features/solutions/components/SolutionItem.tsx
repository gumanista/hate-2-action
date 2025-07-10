import React from 'react';
import { Solution } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface SolutionItemProps {
  solution: Solution;
}

export const SolutionItem: React.FC<SolutionItemProps> = ({ solution }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{solution.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{solution.context}</p>
        {solution.problem_id && <Badge>Problem ID: {solution.problem_id}</Badge>}
      </CardContent>
    </Card>
  );
};