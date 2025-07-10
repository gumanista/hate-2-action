import { Project } from './types';
import { fetcher } from '../../lib/api';

export const getProjects = async (): Promise<Project[]> => {
  return fetcher('/projects');
};

export const getProject = async (id: string): Promise<Project> => {
  return fetcher(`/projects/${id}`);
};