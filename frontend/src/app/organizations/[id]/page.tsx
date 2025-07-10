'use client';

import { useEffect, useState } from 'react';
import { getOrganization } from '@/features/organizations/services';
import { Organization } from '@/features/organizations/types';
import { useParams } from 'next/navigation';

export default function OrganizationDetailsPage() {
    const params = useParams();
    const { id } = params;
    const [organization, setOrganization] = useState<Organization | null>(null);

    useEffect(() => {
        if (id) {
            const fetchOrganization = async () => {
                try {
                    const org = await getOrganization(id as string);
                    setOrganization(org);
                } catch (error) {
                    console.error('Failed to fetch organization', error);
                }
            };
            fetchOrganization();
        }
    }, [id]);

    if (!organization) {
        return <div>Loading...</div>;
    }

    return (
        <div>
            <h1>{organization.name}</h1>
            <p>{organization.description}</p>
        </div>
    );
}