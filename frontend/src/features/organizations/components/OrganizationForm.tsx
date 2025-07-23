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

const formSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string(),
  website: z.string().url({ message: "Please enter a valid URL, including http:// or https://" }).optional().or(z.literal('')),
  contact_email: z.string().email({ message: "Please enter a valid email address" }).optional().or(z.literal('')),
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
  const form = useForm<OrganizationFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: organization?.name || '',
      description: organization?.description || '',
      website: organization?.website || '',
      contact_email: organization?.contact_email || '',
  },
});

  const handleSubmit = (values: OrganizationFormValues) => {
      const organizationData: OrganizationCreate = {
          name: values.name,
          description: values.description,
          website: values.website,
          contact_email: values.contact_email,
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
        <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Save'}
        </Button>
        </form>
    </Form>
    );
}