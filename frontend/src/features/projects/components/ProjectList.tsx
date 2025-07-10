import React from 'react';
import { Project } from '../types';
import { ProjectItem } from './ProjectItem';

interface ProjectListProps {
  projects: Project[];
}

export const ProjectList: React.FC<ProjectListProps> = ({ projects }) => {
  return (
    <div className="grid gap-4">
      {projects.map((project) => (
        <ProjectItem key={project.project_id} project={project} />
      ))}
    </div>
  );
};