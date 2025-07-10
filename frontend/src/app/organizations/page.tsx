'use client';

import Link from 'next/link';
import { useOrganizations } from '../../features/organizations/useOrganizations';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function OrganizationsPage() {
  const { organizations, isLoading, error } = useOrganizations();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error.message}</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Organizations</h1>
        <Button asChild>
          <Link href="/organizations/new">New Organization</Link>
        </Button>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {organizations.map((organization) => (
          <Card key={organization.id}>
            <CardHeader>
              <CardTitle>{organization.name}</CardTitle>
              <CardDescription>{organization.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild>
                <Link href={`/organizations/${organization.id}`}>View</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}