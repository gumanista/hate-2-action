'use client';

import { useEffect, useState } from 'react';
import { getProblem } from '@/features/problems/services/api';
import { Problem } from '@/features/problems/types';
import { useParams, useRouter } from 'next/navigation';
import { ProblemItemFull } from '@/features/problems/components/ProblemItemFull';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

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
                    // Optionally redirect to a 404 page or show an error message
                }
            };
            fetchProblem();
        }
    }, [id]);

    if (!problem) {
        return <div>Loading...</div>;
    }

    return (
        <div className="container mx-auto py-10">
            <div className="flex justify-between items-center mb-4">
                <h1 className="text-2xl font-bold">Problem Details</h1>
                <Button asChild>
                    <Link href={`/problems/${problem.problem_id}/edit`}>
                        Edit Problem
                    </Link>
                </Button>
            </div>
            <ProblemItemFull problem={problem} />
        </div>
    );
}