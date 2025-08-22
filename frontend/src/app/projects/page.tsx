'use client';

import Link from 'next/link';
import { useProjects } from '../../features/projects/useProjects';
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

export default function ProjectsPage() {
 const { projects, isLoading, error } = useProjects();
 const [search, setSearch] = useState('');

 if (isLoading) {
   return <div>Loading...</div>;
 }

 if (error) {
   return <div>Error: {error.message}</div>;
 }

 const filteredProjects = projects.filter((project) =>
   project.name.toLowerCase().includes(search.toLowerCase())
 );

 return (
   <div className="container mx-auto p-4">
     <div className="flex justify-between items-center mb-4">
       <h1 className="text-2xl font-bold">Projects</h1>
       <Button asChild>
         <Link href="/projects/new">New Project</Link>
       </Button>
     </div>
     <div className="mb-4">
       <Input
         type="text"
         placeholder="Search projects..."
         value={search}
         onChange={(e) => setSearch(e.target.value)}
       />
     </div>
     <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
       {filteredProjects.map((project) => (
         <Card key={project.project_id}>
           <CardHeader>
             <CardTitle>{project.name}</CardTitle>
             <CardDescription>{project.description}</CardDescription>
           </CardHeader>
           <CardContent>
             <Button asChild>
               <Link href={`/projects/${project.project_id}`}>View</Link>
             </Button>
           </CardContent>
         </Card>
       ))}
     </div>
   </div>
 );
}