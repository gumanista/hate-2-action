'use client';

import { Organization, OrganizationCreate, OrganizationUpdate } from '../types/index';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useProjects } from '@/features/projects/useProjects';
import { MultiSelect } from '@/components/ui/multi-select';

const formSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string(),
  website: z.string().url({ message: "Please enter a valid URL, including http:// or https://" }).optional().or(z.literal('')),
  contact_email: z.string().email({ message: "Please enter a valid email address" }).optional().or(z.literal('')),
  project_ids: z.array(z.number()).optional(),
});

type OrganizationFormValues = z.infer<typeof formSchema>;

interface OrganizationFormProps {
  organization?: Organization;
  onSubmit: (values: OrganizationCreate | OrganizationUpdate) => void;
  isSubmitting: boolean;
}

export function OrganizationForm({
  organization,
  onSubmit,
  isSubmitting,
}: OrganizationFormProps) {
    const { projects } = useProjects();
  const form = useForm<OrganizationFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: organization?.name || '',
      description: organization?.description || '',
      website: organization?.website || '',
      contact_email: organization?.contact_email || '',
      project_ids: organization?.projects?.map((p) => p.project_id) || [],
  },
});

  const handleSubmit = (values: OrganizationFormValues) => {
      const organizationData: OrganizationCreate = {
          ...values,
      };
      onSubmit(organizationData);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="Organization name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea placeholder="Organization description" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="website"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Website</FormLabel>
              <FormControl>
                <Input placeholder="Organization website" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
            control={form.control}
            name="contact_email"
            render={({ field }) => (
                <FormItem>
                    <FormLabel>Contact Email</FormLabel>
                    <FormControl>
                        <Input placeholder="Organization contact email" {...field} />
                    </FormControl>
                    <FormMessage />
                </FormItem>
            )}
        />
        <FormField
          control={form.control}
          name="project_ids"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Projects</FormLabel>
              <FormControl>
                <MultiSelect
                  options={projects.map((p) => ({ value: p.project_id, label: p.name }))}
                  defaultValue={field.value || []}
                  onValueChange={field.onChange}
                  className="w-full"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Save'}
        </Button>
        </form>
    </Form>
    );
}