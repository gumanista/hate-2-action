import { Solution } from './types';
import { fetcher } from '../../lib/api';

export const getSolutions = async (): Promise<Solution[]> => {
  return fetcher('/solutions');
};
export const getSolution = async (id: number): Promise<Solution> => {
  return fetcher(`/solutions/${id}`);
};