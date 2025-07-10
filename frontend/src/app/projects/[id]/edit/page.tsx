'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getProject, updateProject } from '../../../../features/projects/services/api';
import { Project, ProjectUpdate } from '../../../../features/projects/types/index';
import { ProjectForm } from '../../../../features/projects/components/ProjectForm';

export default function EditProjectPage() {
    const router = useRouter();
    const params = useParams();
    const { id } = params;
    const [project, setProject] = useState<Project | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (id) {
            const fetchProject = async () => {
                try {
                    const projectData = await getProject(Number(id));
                    setProject(projectData);
                } catch (error) {
                    console.error('Failed to fetch project', error);
                }
            };
            fetchProject();
        }
    }, [id]);

    const handleSubmit = async (values: ProjectUpdate) => {
        if (project) {
            setIsSubmitting(true);
            try {
                await updateProject(project.project_id, values);
                router.push('/projects');
            } catch (error) {
                console.error('Failed to update project', error);
            } finally {
                setIsSubmitting(false);
            }
        }
    };

    if (!project) {
        return <div>Loading...</div>;
    }

    return (
        <div>
            <h1>Edit Project</h1>
            <ProjectForm
                project={project}
                onSubmit={handleSubmit}
                isSubmitting={isSubmitting}
            />
        </div>
    );
}