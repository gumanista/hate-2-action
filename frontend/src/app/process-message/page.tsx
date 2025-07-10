import { ProcessMessageForm } from "@/features/process-message/components/ProcessMessageForm";

export default function ProcessMessagePage() {
  return (
    <main className="container mx-auto py-8">
      <h1 className="text-2xl font-bold mb-4">Process Message</h1>
      <ProcessMessageForm />
    </main>
  );
}