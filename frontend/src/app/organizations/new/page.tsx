'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createOrganization } from '../../../features/organizations/services/api';
import { OrganizationCreate, OrganizationUpdate } from '../../../features/organizations/types/index';
import { OrganizationForm } from '../../../features/organizations/components/OrganizationForm';

export default function NewOrganizationPage() {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (values: OrganizationCreate | OrganizationUpdate) => {
        setIsSubmitting(true);
        try {
            await createOrganization(values as OrganizationCreate);
            router.push('/organizations');
        } catch (error) {
            console.error('Failed to create organization', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div>
            <h1>Create Organization</h1>
            <OrganizationForm
                onSubmit={handleSubmit}
                isSubmitting={isSubmitting}
            />
        </div>
    );
}