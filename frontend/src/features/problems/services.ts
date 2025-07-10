import { Problem } from './types';
import { fetcher } from '../../lib/api';

export const getProblems = async (): Promise<Problem[]> => {
  return fetcher('/problems');
};
export const getProblem = async (id: string): Promise<Problem> => {
  return fetcher(`/problems/${id}`);
};