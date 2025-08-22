'use client';

import Link from 'next/link';
import { useOrganizations } from '../../features/organizations/useOrganizations';
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

export default function OrganizationsPage() {
 const { organizations, isLoading, error } = useOrganizations();
 const [search, setSearch] = useState('');

 if (isLoading) {
   return <div>Loading...</div>;
 }

 if (error) {
   return <div>Error: {error.message}</div>;
 }

 const filteredOrganizations = organizations.filter((organization) =>
   organization.name.toLowerCase().includes(search.toLowerCase())
 );

 return (
   <div className="container mx-auto p-4">
     <div className="flex justify-between items-center mb-4">
       <h1 className="text-2xl font-bold">Organizations</h1>
       <Button asChild>
         <Link href="/organizations/new">New Organization</Link>
       </Button>
     </div>
     <div className="mb-4">
       <Input
         type="text"
         placeholder="Search organizations..."
         value={search}
         onChange={(e) => setSearch(e.target.value)}
       />
     </div>
     <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
       {filteredOrganizations.map((organization) => (
         <Card key={organization.organization_id}>
           <CardHeader>
             <CardTitle>{organization.name}</CardTitle>
             <CardDescription>{organization.description}</CardDescription>
           </CardHeader>
           <CardContent>
             <Button asChild>
               <Link href={`/organizations/${organization.organization_id}`}>
                 View
               </Link>
             </Button>
           </CardContent>
         </Card>
       ))}
     </div>
   </div>
 );
}