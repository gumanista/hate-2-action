'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getOrganization } from '../../../features/organizations/services';
import { Organization } from '../../../features/organizations/types';
import { Project } from '../../../features/projects/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function OrganizationPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [organization, setOrganization] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (id) {
      const fetchOrganizationData = async () => {
        setIsLoading(true);
        try {
          const orgData = await getOrganization(id);
          setOrganization(orgData);
        } catch (err) {
          setError(err as Error);
        } finally {
          setIsLoading(false);
        }
      };

      fetchOrganizationData();
    }
  }, [id]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error.message}</div>;
  }

  if (!organization) {
    return <div>Organization not found</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-3xl font-bold">{organization.name}</h1>
        <Button onClick={() => router.push(`/organizations/${organization.organization_id}/edit`)}>
          Edit
        </Button>
      </div>
      {organization.description && (
        <p className="text-lg text-gray-700 mb-2">
          <strong>Description:</strong> {organization.description}
        </p>
      )}
      {organization.website && (
        <p className="text-lg text-gray-700 mb-2">
          <strong>Website:</strong>{' '}
          <a href={organization.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
            {organization.website}
          </a>
        </p>
      )}
      {organization.contact_email && (
        <p className="text-lg text-gray-700 mb-2">
          <strong>Contact Email:</strong> {organization.contact_email}
        </p>
      )}
      <h2 className="text-2xl font-bold mt-6 mb-2">Projects</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {organization.projects && organization.projects.length > 0 ? (
          organization.projects.map((project: Project) => (
            <Card key={project.project_id}>
              <CardHeader>
                <CardTitle>{project.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{project.description}</p>
                <Button asChild className="mt-4">
                  <Link href={`/projects/${project.project_id}`}>View Project</Link>
                </Button>
              </CardContent>
            </Card>
          ))
        ) : (
          <p>No projects found for this organization.</p>
        )}
      </div>
    </div>
  );
}