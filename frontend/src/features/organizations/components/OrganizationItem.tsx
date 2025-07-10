import React from 'react';
import { Organization } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface OrganizationItemProps {
  organization: Organization;
}

export const OrganizationItem: React.FC<OrganizationItemProps> = ({ organization }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{organization.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{organization.description}</p>
      </CardContent>
    </Card>
  );
};