'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createProject } from '../../../features/projects/services/api';
import { ProjectCreate, ProjectUpdate } from '../../../features/projects/types/index';
import { ProjectForm } from '../../../features/projects/components/ProjectForm';
import { getOrganizations } from '@/features/organizations/services/api';
import { Organization } from '@/features/organizations/types';

export default function NewProjectPage() {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [organizations, setOrganizations] = useState<Organization[]>([]);

    useEffect(() => {
        const fetchOrganizations = async () => {
            try {
                const orgs = await getOrganizations();
                setOrganizations(orgs);
            } catch (error) {
                console.error('Failed to fetch organizations', error);
            }
        };

        fetchOrganizations();
    }, []);

    const handleSubmit = async (values: ProjectCreate | ProjectUpdate) => {
        setIsSubmitting(true);
        try {
            await createProject(values as ProjectCreate);
            router.push('/projects');
        } catch (error) {
            console.error('Failed to create project', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="p-4 sm:p-6 md:p-8">
            <h1 className="text-2xl font-bold mb-4">Create Project</h1>
            <ProjectForm
                onSubmit={handleSubmit}
                isSubmitting={isSubmitting}
                organizations={organizations}
            />
        </div>
    );
}