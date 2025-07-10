import React from 'react';
import { Organization } from '../types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ProjectList } from '@/features/projects/components/ProjectList';

interface OrganizationItemFullProps {
  organization: Organization;
}

export const OrganizationItemFull: React.FC<OrganizationItemFullProps> = ({ organization }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{organization.name}</CardTitle>
        <CardDescription>{organization.description}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div>
          <h4 className="font-semibold">Details</h4>
          <div className="flex items-center space-x-2">
            {organization.website && <a href={organization.website} target="_blank" rel="noopener noreferrer"><Badge>Website</Badge></a>}
            {organization.contact_email && <a href={`mailto:${organization.contact_email}`} ><Badge>Email</Badge></a>}
          </div>
        </div>
        {organization.projects && organization.projects.length > 0 && (
          <div>
            <h4 className="font-semibold">Projects</h4>
            <ProjectList projects={organization.projects} />
          </div>
        )}
      </CardContent>
    </Card>
  );
};