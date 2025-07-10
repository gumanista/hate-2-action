import React from 'react';
import { Problem } from '../types';
import { ProblemItem } from './ProblemItem';

interface ProblemListProps {
  problems: Problem[];
}

export const ProblemList: React.FC<ProblemListProps> = ({ problems }) => {
  return (
    <div className="grid gap-4">
      {problems.map((problem) => (
        <ProblemItem key={problem.problem_id} problem={problem} />
      ))}
    </div>
  );
};