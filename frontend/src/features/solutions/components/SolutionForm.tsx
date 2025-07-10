'use client';

import { Solution, SolutionCreate, SolutionUpdate } from '../types/index';
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
  context: z.string(),
});

type SolutionFormValues = z.infer<typeof formSchema>;

interface SolutionFormProps {
  solution?: Solution;
  onSubmit: (values: SolutionCreate | SolutionUpdate) => void;
  isSubmitting: boolean;
}

export function SolutionForm({
  solution,
  onSubmit,
  isSubmitting,
}: SolutionFormProps) {
  const form = useForm<SolutionFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: solution?.name || '',
      context: solution?.context || '',
    },
  });

  const handleSubmit = (values: SolutionFormValues) => {
    onSubmit(values);
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
                <Input placeholder="Solution name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="context"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Context</FormLabel>
              <FormControl>
                <Textarea placeholder="Solution context" {...field} />
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