import React from 'react';
import { Organization } from '../types';
import { OrganizationItem } from './OrganizationItem';

interface OrganizationListProps {
  organizations: Organization[];
}

export const OrganizationList: React.FC<OrganizationListProps> = ({ organizations }) => {
  return (
    <div className="grid gap-4">
      {organizations.map((organization) => (
        <OrganizationItem key={organization.id} organization={organization} />
      ))}
    </div>
  );
};