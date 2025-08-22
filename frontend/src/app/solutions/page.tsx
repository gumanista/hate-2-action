'use client';

import Link from 'next/link';
import { useSolutions } from '@/features/solutions/useSolutions';
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

export default function SolutionsPage() {
 const { solutions, isLoading, error } = useSolutions();
 const [search, setSearch] = useState('');

 if (isLoading) {
   return <div>Loading...</div>;
 }

 if (error) {
   return <div>Error: {error.message}</div>;
 }

 const filteredSolutions = solutions.filter((solution) =>
   solution.name.toLowerCase().includes(search.toLowerCase())
 );

 return (
   <div className="container mx-auto p-4">
     <div className="flex justify-between items-center mb-4">
       <h1 className="text-2xl font-bold">Solutions</h1>
       <Button asChild>
         <Link href="/solutions/new">New Solution</Link>
       </Button>
     </div>
     <div className="mb-4">
       <Input
         type="text"
         placeholder="Search solutions..."
         value={search}
         onChange={(e) => setSearch(e.target.value)}
       />
     </div>
     <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
       {filteredSolutions.map((solution) => (
         <Card key={solution.solution_id}>
           <CardHeader>
             <CardTitle>{solution.name}</CardTitle>
             <CardDescription>{solution.context}</CardDescription>
           </CardHeader>
           <CardContent>
             <Button asChild>
               <Link href={`/solutions/${solution.solution_id}`}>View</Link>
             </Button>
           </CardContent>
         </Card>
       ))}
     </div>
   </div>
 );
}