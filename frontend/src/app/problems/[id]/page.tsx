'use client';

import { useEffect, useState } from 'react';
import { getProblem } from '@/features/problems/services';
import { Problem } from '@/features/problems/types';
import { useParams } from 'next/navigation';

export default function ProblemDetailsPage() {
    const params = useParams();
    const { id } = params;
    const [problem, setProblem] = useState<Problem | null>(null);

    useEffect(() => {
        if (id) {
            const fetchProblem = async () => {
                try {
                    const problemData = await getProblem(Number(id));
                    setProblem(problemData);
                } catch (error) {
                    console.error('Failed to fetch problem', error);
                }
            };
            fetchProblem();
        }
    }, [id]);

    if (!problem) {
        return <div>Loading...</div>;
    }

    return (
        <div>
            <h1>{problem.name}</h1>
            <p>{problem.description}</p>
        </div>
    );
}