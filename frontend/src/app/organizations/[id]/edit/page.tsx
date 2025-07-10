'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getOrganization, updateOrganization } from '../../../../features/organizations/services/api';
import { Organization, OrganizationUpdate } from '../../../../features/organizations/types';
import { OrganizationForm } from '../../../../features/organizations/components/OrganizationForm';

export default function EditOrganizationPage() {
    const router = useRouter();
    const params = useParams();
    const { id } = params;
    const [organization, setOrganization] = useState<Organization | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (id) {
            const fetchOrganization = async () => {
                try {
                    const org = await getOrganization(Number(id));
                    setOrganization(org);
                } catch (error) {
                    console.error('Failed to fetch organization', error);
                }
            };
            fetchOrganization();
        }
    }, [id]);

    const handleSubmit = async (values: OrganizationUpdate) => {
        if (organization) {
            setIsSubmitting(true);
            try {
                await updateOrganization(organization.id, values);
                router.push('/organizations');
            } catch (error) {
                console.error('Failed to update organization', error);
            } finally {
                setIsSubmitting(false);
            }
        }
    };

    if (!organization) {
        return <div>Loading...</div>;
    }

    return (
        <div>
            <h1>Edit Organization</h1>
            <OrganizationForm
                organization={organization}
                onSubmit={handleSubmit}
                isSubmitting={isSubmitting}
            />
        </div>
    );
}