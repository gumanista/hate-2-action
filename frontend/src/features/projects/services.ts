import { Project, ProjectCreate, ProjectUpdate } from './types/index';
import * as api from './services/api';

export const getProjects = (): Promise<Project[]> => {
    return api.getProjects();
};

export const getProject = (id: number): Promise<Project> => {
    return api.getProject(id);
};

export const createProject = (project: ProjectCreate): Promise<Project> => {
    return api.createProject(project);
};

export const updateProject = (id: number, project: ProjectUpdate): Promise<Project> => {
    return api.updateProject(id, project);
};

export const deleteProject = (id: number): Promise<void> => {
    return api.deleteProject(id);
};