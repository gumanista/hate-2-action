'use client';

import Link from 'next/link';
import { useProblems } from '@/features/problems/hooks/useProblems';
import {
 Card,
 CardContent,
 CardDescription,
 CardHeader,
 CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useState } from 'react';

export default function ProblemsPage() {
 const { problems, isLoading, error } = useProblems();
 const [search, setSearch] = useState('');

 if (isLoading) {
   return <div>Loading...</div>;
 }

 if (error) {
   return <div>Error: {error.message}</div>;
 }

 const filteredProblems = problems.filter((problem) =>
   problem.name.toLowerCase().includes(search.toLowerCase())
 );

 return (
   <div className="container mx-auto p-4">
     <div className="flex justify-between items-center mb-4">
       <h1 className="text-2xl font-bold">Problems</h1>
       <Button asChild>
         <Link href="/problems/new">New Problem</Link>
       </Button>
     </div>
     <div className="mb-4">
       <Input
         type="text"
         placeholder="Search problems..."
         value={search}
         onChange={(e) => setSearch(e.target.value)}
       />
     </div>
     <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
       {filteredProblems.map((problem) => (
         <Card key={problem.problem_id}>
           <CardHeader>
             <CardTitle>{problem.name}</CardTitle>
             <CardDescription>{problem.context}</CardDescription>
           </CardHeader>
           <CardContent>
             <Button asChild>
               <Link href={`/problems/${problem.problem_id}`}>View</Link>
             </Button>
           </CardContent>
         </Card>
       ))}
     </div>
   </div>
 );
}