import { Problem } from '@/types';
import { fetcher } from '@/lib/api';

export const getProblems = async (): Promise<Problem[]> => {
  return fetcher('/problems');
};