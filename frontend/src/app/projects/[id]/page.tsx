'use client';

import { useEffect, useState } from 'react';
import { getProject } from '@/features/projects/services';
import { Project } from '@/features/projects/types';
import { useParams } from 'next/navigation';

export default function ProjectDetailsPage() {
    const params = useParams();
    const { id } = params;
    const [project, setProject] = useState<Project | null>(null);

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

    if (!project) {
        return <div>Loading...</div>;
    }

    return (
        <div>
            <h1>{project.name}</h1>
            <p>{project.description}</p>
        </div>
    );
}