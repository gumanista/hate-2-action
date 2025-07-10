import React from 'react';
import { Problem } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ProblemItemProps {
  problem: Problem;
}

export const ProblemItem: React.FC<ProblemItemProps> = ({ problem }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{problem.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{problem.context}</p>
        <Badge>{problem.is_processed ? 'Processed' : 'Not Processed'}</Badge>
      </CardContent>
    </Card>
  );
};