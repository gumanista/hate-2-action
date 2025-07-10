import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <section className="container grid items-center gap-6 pb-8 pt-6 md:py-10">
      <div className="flex max-w-[980px] flex-col items-start gap-2">
        <h1 className="text-3xl font-extrabold leading-tight tracking-tighter sm:text-3xl md:text-5xl lg:text-6xl">
          Hate to Action
        </h1>
        <p className="max-w-[700px] text-lg text-muted-foreground sm:text-xl">
          A platform to connect people with social problems to projects that can solve them.
        </p>
      </div>
      <div className="flex gap-4">
        <Link
          href="/projects"
        >
          <Button>View Projects</Button>
        </Link>
        <Link
          href="/organizations"
        >
          <Button>View Organizations</Button>
        </Link>
        <Link
          href="/problems"
        >
          <Button>View Problems</Button>
        </Link>
        <Link
          href="/solutions"
        >
          <Button>View Solutions</Button>
        </Link>
      </div>
    </section>
  )
}
