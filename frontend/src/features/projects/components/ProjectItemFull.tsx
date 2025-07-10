import React from 'react';
import { Project } from '../types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ProblemList } from '@/features/problems/components/ProblemList';

interface ProjectItemFullProps {
  project: Project;
}

export const ProjectItemFull: React.FC<ProjectItemFullProps> = ({ project }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{project.name}</CardTitle>
        <CardDescription>{project.description}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div>
          <h4 className="font-semibold">Details</h4>
          <div className="flex items-center space-x-2">
            <Badge variant="outline">Organization ID: {project.organization_id}</Badge>
            {project.website && <a href={project.website} target="_blank" rel="noopener noreferrer"><Badge>Website</Badge></a>}
            {project.contact_email && <a href={`mailto:${project.contact_email}`}><Badge>Email</Badge></a>}
          </div>
        </div>
        {project.problems && project.problems.length > 0 && (
          <div>
            <h4 className="font-semibold">Problems</h4>
            <ProblemList problems={project.problems} />
          </div>
        )}
      </CardContent>
    </Card>
  );
};