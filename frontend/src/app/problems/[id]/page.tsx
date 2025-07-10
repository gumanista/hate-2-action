'use client';

import { useEffect, useState } from 'react';
import { getProblem } from '@/features/problems/services/api';
import { Problem } from '@/features/problems/types';
import { useParams } from 'next/navigation';

export default function ProblemDetailsPage() {
    const params = useParams();
    const { id } = params;
    const [problem, setProblem] = useState<Problem | null>(null);

    useEffect(() => {
        const problemId = Array.isArray(id) ? id[0] : id;
        if (problemId) {
            const fetchProblem = async () => {
                try {
                    const problemData = await getProblem(Number(problemId));
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
            <p>{problem.context}</p>
        </div>
    );
}