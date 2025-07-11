'use client';

import { useEffect, useState } from 'react';
import { getProject } from '@/features/projects/services';
import { Project } from '@/features/projects/types';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

export default function ProjectDetailsPage() {
    const params = useParams();
    const { id } = params;
    const router = useRouter();
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
        <div className="container mx-auto p-4">
            <div className="flex justify-between items-center mb-4">
                <h1 className="text-3xl font-bold">{project.name}</h1>
                <Button onClick={() => router.push(`/projects/${project.project_id}/edit`)}>
                    Edit
                </Button>
            </div>
            {project.description && (
                <p className="text-lg text-gray-700 mb-2">
                    <strong>Description:</strong> {project.description}
                </p>
            )}
            {project.website && (
                <p className="text-lg text-gray-700 mb-2">
                    <strong>Website:</strong>{' '}
                    <a href={project.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                        {project.website}
                    </a>
                </p>
            )}
            {project.contact_email && (
                <p className="text-lg text-gray-700 mb-2">
                    <strong>Contact Email:</strong> {project.contact_email}
                </p>
            )}
            {project.created_at && (
                <p className="text-lg text-gray-700 mb-2">
                    <strong>Created At:</strong> {new Date(project.created_at).toLocaleDateString()}
                </p>
            )}
            {project.organization && (
                <p className="text-lg text-gray-700 mb-2">
                    <strong>Organization:</strong> {project.organization.name}
                </p>
            )}
            {project.problems && project.problems.length > 0 && (
                <div className="mt-4">
                    <h2 className="text-2xl font-bold mb-2">Associated Problems</h2>
                    <ul>
                        {project.problems.map((problem) => (
                            <li key={problem.problem_id} className="text-lg text-gray-700">
                                <a href={`/problems/${problem.problem_id}`} className="text-blue-600 hover:underline">
                                    {problem.name}
                                </a>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}