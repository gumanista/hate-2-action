'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { getProblem, updateProblem } from '@/features/problems/services/api';
import { Problem, ProblemUpdate } from '@/features/problems/types';
import { ProblemForm } from '@/features/problems/components/ProblemForm';

export default function EditProblemPage() {
    const router = useRouter();
    const params = useParams();
    const { id } = params;
    const [problem, setProblem] = useState<Problem | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

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

    const handleSubmit = async (values: ProblemUpdate) => {
        if (problem) {
            setIsSubmitting(true);
            try {
                await updateProblem(problem.problem_id, values);
                router.push('/problems');
            } catch (error) {
                console.error('Failed to update problem', error);
            } finally {
                setIsSubmitting(false);
            }
        }
    };

    if (!problem) {
        return <div>Loading...</div>;
    }

    return (
        <div>
            <h1>Edit Problem</h1>
            <ProblemForm
                problem={problem}
                onSubmit={handleSubmit}
                isSubmitting={isSubmitting}
            />
        </div>
    );
}