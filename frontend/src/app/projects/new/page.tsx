'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createProject } from '../../../features/projects/services/api';
import { ProjectCreate, ProjectUpdate } from '../../../features/projects/types/index';
import { ProjectForm } from '../../../features/projects/components/ProjectForm';

export default function NewProjectPage() {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);

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
        <div>
            <h1>Create Project</h1>
            <ProjectForm
                onSubmit={handleSubmit}
                isSubmitting={isSubmitting}
            />
        </div>
    );
}