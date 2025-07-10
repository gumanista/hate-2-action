'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createProblem } from '../../../features/problems/services/api';
import { ProblemCreate, ProblemUpdate } from '../../../features/problems/types';
import { ProblemForm } from '../../../features/problems/components/ProblemForm';

export default function NewProblemPage() {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (values: ProblemCreate | ProblemUpdate) => {
        setIsSubmitting(true);
        try {
            await createProblem(values as ProblemCreate);
            router.push('/problems');
        } catch (error) {
            console.error('Failed to create problem', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div>
            <h1>Create Problem</h1>
            <ProblemForm
                onSubmit={handleSubmit}
                isSubmitting={isSubmitting}
            />
        </div>
    );
}