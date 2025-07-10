import React from 'react';
import { Solution } from '../types';
import { SolutionItem } from './SolutionItem';

interface SolutionListProps {
  solutions: Solution[];
}

export const SolutionList: React.FC<SolutionListProps> = ({ solutions }) => {
  return (
    <div className="grid gap-4">
      {solutions.map((solution) => (
        <SolutionItem key={solution.solution_id} solution={solution} />
      ))}
    </div>
  );
};